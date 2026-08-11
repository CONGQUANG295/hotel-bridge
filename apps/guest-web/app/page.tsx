'use client';

import { useEffect, useMemo, useState } from 'react';
import type { GuestSession, Order, Service } from '@hotel-bridge/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const SESSION_PREFIX = 'hotel-bridge:guest-session:';
const CONVERSATION_PREFIX = 'hotel-bridge:conversation:';

type ChatMessage = { id: string; conversationId: string; sender: string; originalText: string; translatedText: string; sourceLocale: string; targetLocale: string; createdAt: string };

function statusLabel(status: Order['status']) {
  return status.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
}

function dueLabel(value: string) {
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export default function GuestHome() {
  const [locale, setLocale] = useState('en');
  const [roomNumber, setRoomNumber] = useState('302');
  const [session, setSession] = useState<GuestSession | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatText, setChatText] = useState('');
  const [chatOpen, setChatOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [error, setError] = useState('');

  async function createSession(room: string, language: string) {
    const response = await fetch(`${API_URL}/api/guest-sessions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roomNumber: room, locale: language }),
    });
    if (!response.ok) throw new Error('Could not start your room session');
    const created: GuestSession = await response.json();
    localStorage.setItem(`${SESSION_PREFIX}${room}`, JSON.stringify(created));
    setSession(created);
    return created;
  }

  async function loadGuestData(room: string, language: string) {
    setLoading(true); setError('');
    try {
      const servicesResponse = await fetch(`${API_URL}/api/services`, { cache: 'no-store' });
      if (!servicesResponse.ok) throw new Error('Could not load hotel services');
      setServices((await servicesResponse.json()).services);

      const saved = localStorage.getItem(`${SESSION_PREFIX}${room}`);
      let active: GuestSession | null = saved ? JSON.parse(saved) : null;
      if (!active || new Date(active.expiresAt) <= new Date()) active = await createSession(room, language);
      setSession(active); setLocale(active.locale);

      const ordersResponse = await fetch(`${API_URL}/api/orders?sessionToken=${encodeURIComponent(active.token)}`, { cache: 'no-store' });
      if (!ordersResponse.ok) throw new Error('Could not load your requests');
      setOrders((await ordersResponse.json()).orders);

      const savedConversation = localStorage.getItem(`${CONVERSATION_PREFIX}${room}`);
      let activeConversation = savedConversation;
      if (!activeConversation) {
        const conversationResponse = await fetch(`${API_URL}/api/conversations`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionToken: active.token }),
        });
        if (!conversationResponse.ok) throw new Error('Could not start hotel chat');
        const createdConversation: { id: string } = await conversationResponse.json();
        activeConversation = createdConversation.id;
        localStorage.setItem(`${CONVERSATION_PREFIX}${room}`, createdConversation.id);
      }
      if (!activeConversation) throw new Error('Could not start hotel chat');
      setConversationId(activeConversation);
      const messagesResponse = await fetch(`${API_URL}/api/conversations/${activeConversation}/messages?sessionToken=${encodeURIComponent(active.token)}`, { cache: 'no-store' });
      if (!messagesResponse.ok) throw new Error('Could not load hotel chat');
      setMessages((await messagesResponse.json()).messages);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Something went wrong');
    } finally { setLoading(false); }
  }

  useEffect(() => {
    const room = new URLSearchParams(window.location.search).get('room')?.trim() || '302';
    setRoomNumber(room);
    void loadGuestData(room, locale);
  }, []);

  useEffect(() => {
    if (!session) return;
    const refreshOrders = async () => {
      const response = await fetch(`${API_URL}/api/orders?sessionToken=${encodeURIComponent(session.token)}`, { cache: 'no-store' });
      if (response.ok) setOrders((await response.json()).orders);
    };
    const interval = window.setInterval(() => void refreshOrders(), 5000);
    return () => window.clearInterval(interval);
  }, [session]);

  async function requestService(service: Service) {
    if (!session) return;
    setSubmitting(service.id); setError('');
    try {
      const response = await fetch(`${API_URL}/api/orders`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionToken: session.token, serviceId: service.id, quantity: 1 }),
      });
      if (!response.ok) throw new Error('Could not send this request');
      const created: Order = await response.json();
      setOrders(current => [created, ...current]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not send this request');
    } finally { setSubmitting(null); }
  }

  async function sendChat() {
    if (!session || !conversationId || !chatText.trim()) return;
    const originalText = chatText.trim();
    setChatText(''); setError('');
    try {
      const response = await fetch(`${API_URL}/api/conversations/${conversationId}/messages`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionToken: session.token, originalText, sourceLocale: locale, targetLocale: 'vi' }),
      });
      if (!response.ok) throw new Error('Could not send your message');
      const message: ChatMessage = await response.json();
      setMessages(current => [...current, message]);
    } catch (caught) {
      setChatText(originalText);
      setError(caught instanceof Error ? caught.message : 'Could not send your message');
    }
  }

  const activeOrders = useMemo(() => orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status)), [orders]);
  const serviceName = (serviceId: string) => services.find(service => service.id === serviceId)?.name ?? serviceId;

  return <main className="guest-shell">
    <header><strong>Hotel Bridge</strong><span>Room {roomNumber} · <select value={locale} onChange={event => { setLocale(event.target.value); void createSession(roomNumber, event.target.value); }}><option value="en">English</option><option value="vi">Tiếng Việt</option></select></span></header>
    <section className="hero"><p className="eyebrow">NO DOWNLOAD REQUIRED</p><h1>{locale === 'vi' ? 'Kỳ nghỉ đơn giản hơn.' : 'Your stay, made simple.'}</h1><p>Scan, choose your language, chat with the hotel, or request a service directly from your room.</p><div className="actions"><button onClick={() => document.getElementById('services')?.scrollIntoView()}>Browse services</button><button className="secondary">Chat with the hotel</button></div></section>
    {error && <p role="alert" className="error-banner">{error}</p>}
    <section id="services"><div className="section-heading"><div><p className="eyebrow">AT YOUR SERVICE</p><h2>Hotel services</h2></div><span>{activeOrders.length} active requests</span></div>{loading ? <p>Loading services…</p> : <div className="service-grid">{services.map(service => { const requested = orders.some(order => order.serviceId === service.id && order.status !== 'CANCELLED'); return <article className="service-card" key={service.id}><div><h3>{service.name}</h3><p>{service.localizedName}</p></div><footer><span>{service.priceLabel} · {service.etaMinutes} min</span><button disabled={submitting === service.id} onClick={() => void requestService(service)}>{submitting === service.id ? 'Sending…' : requested ? 'Requested ✓' : 'Request'}</button></footer></article>; })}</div>}</section>
    <section className="chat-card"><p className="eyebrow">MY REQUESTS · LIVE</p><h2>Track your requests</h2>{orders.length === 0 ? <p>Your requests will appear here after you order a service.</p> : <div>{orders.slice(0, 5).map(order => <article key={order.id}><p><strong>{serviceName(order.serviceId)}</strong> · {order.id}</p><p>Room {order.roomNumber} · Due by {dueLabel(order.dueAt)}</p><p><strong>{statusLabel(order.status)}</strong>{order.note ? ` · ${order.note}` : ''}</p></article>)}</div>}<button className="secondary" onClick={() => setChatOpen(current => !current)}>{chatOpen ? 'Hide chat' : 'Chat with the hotel →'}</button>{chatOpen && <div className="chat-panel"><div>{messages.length === 0 ? <p>No messages yet. Ask the hotel anything.</p> : messages.map(message => <article key={message.id}><p><strong>{message.sender === 'guest' ? 'You' : 'Hotel'}</strong> · {new Date(message.createdAt).toLocaleTimeString()}</p><p>{message.originalText}</p>{message.translatedText !== message.originalText && <small>{message.translatedText}</small>}</article>)}</div><div className="chat-input"><input value={chatText} onChange={event => setChatText(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void sendChat(); }} placeholder="Write a message…" aria-label="Message" /><button onClick={() => void sendChat()} disabled={!chatText.trim()}>Send</button></div></div>}</section>
  </main>;
}

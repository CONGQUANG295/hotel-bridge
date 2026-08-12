'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Order, OrderStatus, StaffRole } from '@hotel-bridge/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const role: StaffRole = 'front_desk';
const labels: Record<OrderStatus, string> = { NEW: 'New request', ACCEPTED: 'Accepted', IN_PROGRESS: 'In progress', READY: 'Ready', DELIVERED: 'Delivered', COMPLETED: 'Completed', CANCELLED: 'Cancelled', ESCALATED: 'Escalated' };
type Conversation = { id: string; roomNumber: string; messageCount: number; updatedAt: string };
type ChatMessage = { id: string; sender: string; originalText: string; translatedText: string; createdAt: string };

function formatTime(value: string) { return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(new Date(value)); }

export default function ManagementHome() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [reply, setReply] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadData() {
    try {
      setError('');
      const headers = { 'X-Staff-Role': role };
      const [ordersResponse, conversationsResponse] = await Promise.all([
        fetch(`${API_URL}/api/management/inbox`, { headers, cache: 'no-store' }),
        fetch(`${API_URL}/api/management/conversations`, { headers, cache: 'no-store' }),
      ]);
      if (!ordersResponse.ok || !conversationsResponse.ok) throw new Error('Could not load the operations inbox');
      setOrders((await ordersResponse.json()).orders);
      const nextConversations: Conversation[] = (await conversationsResponse.json()).conversations;
      setConversations(nextConversations);
      if (!selectedConversation && nextConversations[0]) setSelectedConversation(nextConversations[0].id);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not load the operations inbox'); }
    finally { setLoading(false); }
  }

  async function loadMessages(conversationId: string) {
    const response = await fetch(`${API_URL}/api/management/conversations/${conversationId}/messages`, { headers: { 'X-Staff-Role': role }, cache: 'no-store' });
    if (response.ok) setMessages((await response.json()).messages);
  }

  useEffect(() => { void loadData(); }, []);
  useEffect(() => { if (selectedConversation) void loadMessages(selectedConversation); }, [selectedConversation]);

  async function updateStatus(orderId: string, status: OrderStatus) {
    const response = await fetch(`${API_URL}/api/orders/${orderId}/events`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Staff-Role': role }, body: JSON.stringify({ status }) });
    if (!response.ok) { setError('Status update failed'); return; }
    const changed: Order = await response.json(); setOrders(current => current.map(order => order.id === changed.id ? changed : order));
  }

  async function sendReply() {
    if (!selectedConversation || !reply.trim()) return;
    const originalText = reply.trim(); setReply('');
    const response = await fetch(`${API_URL}/api/management/conversations/${selectedConversation}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Staff-Role': role }, body: JSON.stringify({ originalText, sourceLocale: 'vi', targetLocale: 'en' }) });
    if (!response.ok) { setReply(originalText); setError('Could not send reply'); return; }
    const message: ChatMessage = await response.json();
    setMessages(current => [...current, message]);
    void loadData();
  }

  const openOrders = useMemo(() => orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status)), [orders]);
  const escalations = orders.filter(order => order.status === 'ESCALATED').length;
  const currentConversation = conversations.find(item => item.id === selectedConversation);

  return <main className="management-shell"><aside><strong>Hotel Bridge</strong><p className="muted">Management</p><nav><a className="active">Inbox</a><a>Orders</a><a>Escalations</a><a>Services</a><a>Staff</a></nav><small>Signed in as Linh · Front desk</small></aside><section className="dashboard"><header><div><p className="eyebrow">OPERATIONS · TODAY</p><h1>Good morning, Linh.</h1></div><button>All departments⌄</button></header><div className="stats"><article><span>Open requests</span><strong>{openOrders.length}</strong><small>Live from API</small></article><article><span>Total requests</span><strong>{orders.length}</strong><small>Persisted in SQLite</small></article><article><span>Escalations</span><strong>{escalations}</strong><small className="warning">Needs attention</small></article></div><section className="panel"><div className="panel-heading"><div><p className="eyebrow">INBOX</p><h2>Requests needing attention</h2></div><button className="light" onClick={() => void loadData()}>Refresh ↻</button></div>{error && <p role="alert" className="warning">{error}</p>}{loading ? <p>Loading inbox…</p> : orders.length === 0 ? <p>No orders yet. New guest requests will appear here.</p> : <div className="table">{orders.map(order => <div className="row" key={order.id}><div><strong>{order.serviceId}</strong><span>Room {order.roomNumber} · {order.id}</span></div><span className="department">{order.assignedRole}</span><span>{formatTime(order.dueAt)}</span><select aria-label={`Update ${order.id}`} value={order.status} onChange={event => void updateStatus(order.id, event.target.value as OrderStatus)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>)}</div>}</section><section className="panel chat-inbox"><div className="panel-heading"><div><p className="eyebrow">GUEST CHAT</p><h2>Conversations</h2></div><span>{conversations.length} rooms</span></div><div className="chat-layout"><div className="conversation-list">{conversations.length === 0 ? <p>No guest conversations yet.</p> : conversations.map(conversation => <button className={conversation.id === selectedConversation ? 'conversation active' : 'conversation'} key={conversation.id} onClick={() => setSelectedConversation(conversation.id)}><strong>Room {conversation.roomNumber}</strong><span>{conversation.messageCount} messages · {formatTime(conversation.updatedAt)}</span></button>)}</div><div className="conversation-detail">{!currentConversation ? <p>Select a conversation to view messages.</p> : <><p className="muted">Room {currentConversation.roomNumber} · Original and translated text remain visible</p><div className="messages">{messages.length === 0 ? <p>No messages yet.</p> : messages.map(message => <article key={message.id}><strong>{message.sender === 'guest' ? 'Guest' : 'You'}</strong><p>{message.originalText}</p>{message.translatedText !== message.originalText && <small>{message.translatedText}</small>}</article>)}</div><div className="reply-box"><input value={reply} onChange={event => setReply(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') void sendReply(); }} placeholder="Reply to guest…" aria-label="Reply to guest" /><button onClick={() => void sendReply()} disabled={!reply.trim()}>Send</button></div></>}</div></div></section></section></main>;
}

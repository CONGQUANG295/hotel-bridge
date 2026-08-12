import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Linking from 'expo-linking';
import type { ChatMessage, Conversation, GuestSession, Order, Service } from '@hotel-bridge/shared-types';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000';
const SESSION_STORAGE_KEY = 'hotel-bridge:guest-session';

function statusLabel(status: Order['status']) {
  return status.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
}

export default function GuestMobileHome() {
  const [roomNumber, setRoomNumber] = useState('302');
  const [session, setSession] = useState<GuestSession | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState('');
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [error, setError] = useState('');
  const [restoring, setRestoring] = useState(true);

  async function persistSession(active: GuestSession) {
    await AsyncStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(active));
  }

  async function clearStoredSession() {
    await AsyncStorage.removeItem(SESSION_STORAGE_KEY);
    setSession(null); setConversation(null); setMessages([]); setOrders([]);
  }

  async function hydrateSession(roomFromLink?: string) {
    try {
      const stored = await AsyncStorage.getItem(SESSION_STORAGE_KEY);
      if (!stored) return;
      const active: GuestSession = JSON.parse(stored);
      if (new Date(active.expiresAt).getTime() <= Date.now() || (roomFromLink && active.roomNumber !== roomFromLink)) {
        await AsyncStorage.removeItem(SESSION_STORAGE_KEY); return;
      }
      const servicesResponse = await fetch(`${API_URL}/api/services`);
      if (!servicesResponse.ok) throw new Error('Could not load hotel services');
      setSession(active); setServices((await servicesResponse.json()).services);
    } catch (caught) { await AsyncStorage.removeItem(SESSION_STORAGE_KEY); setError(caught instanceof Error ? caught.message : 'Could not restore room session'); }
    finally { setRestoring(false); }
  }

  useEffect(() => {
    const roomFromUrl = (url?: string | null) => {
      if (!url) return undefined;
      const match = url.match(/(?:room\/|room=)([A-Za-z0-9-]+)/i);
      return match?.[1];
    };
    const initialize = async () => {
      const initialUrl = await Linking.getInitialURL();
      const room = roomFromUrl(initialUrl);
      if (room) setRoomNumber(room);
      await hydrateSession(room);
    };
    void initialize();
    const subscription = Linking.addEventListener('url', event => {
      const room = roomFromUrl(event.url);
      if (room) { setRoomNumber(room); void clearStoredSession(); }
    });
    return () => subscription.remove();
  }, []);

  async function startStay() {
    setLoading(true); setError('');
    try {
      const sessionResponse = await fetch(`${API_URL}/api/guest-sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ roomNumber, locale: 'en' }) });
      if (!sessionResponse.ok) throw new Error('Could not start room session');
      const active: GuestSession = await sessionResponse.json();
      const servicesResponse = await fetch(`${API_URL}/api/services`);
      if (!servicesResponse.ok) throw new Error('Could not load hotel services');
      setSession(active); await persistSession(active); setServices((await servicesResponse.json()).services); setOrders([]); setConversation(null); setMessages([]);
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'Could not connect to Hotel Bridge'); }
    finally { setLoading(false); }
  }

  async function requestService(service: Service) {
    if (!session) return;
    try {
      const response = await fetch(`${API_URL}/api/orders`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionToken: session.token, serviceId: service.id, quantity: 1 }) });
      if (!response.ok) throw new Error('Could not send request');
      const created: Order = await response.json();
      setOrders(current => [created, ...current]);
    } catch (caught) { Alert.alert('Request failed', caught instanceof Error ? caught.message : 'Could not send request'); }
  }

  useEffect(() => {
    if (!session) return;
    const refreshOrders = async () => {
      const response = await fetch(`${API_URL}/api/orders?sessionToken=${encodeURIComponent(session.token)}`);
      if (response.ok) setOrders((await response.json()).orders);
    };
    const timer = setInterval(() => void refreshOrders(), 5000);
    return () => clearInterval(timer);
  }, [session]);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    const openChat = async () => {
      setChatLoading(true);
      try {
        const createdResponse = await fetch(`${API_URL}/api/conversations`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionToken: session.token }) });
        if (!createdResponse.ok) throw new Error('Could not start hotel chat');
        const created: Conversation = await createdResponse.json();
        const messagesResponse = await fetch(`${API_URL}/api/conversations/${created.id}/messages?sessionToken=${encodeURIComponent(session.token)}`);
        if (!messagesResponse.ok) throw new Error('Could not load hotel chat');
        if (!cancelled) { setConversation(created); setMessages((await messagesResponse.json()).messages); }
      } catch (caught) { if (!cancelled) setError(caught instanceof Error ? caught.message : 'Could not start hotel chat'); }
      finally { if (!cancelled) setChatLoading(false); }
    };
    void openChat();
    return () => { cancelled = true; };
  }, [session]);

  useEffect(() => {
    if (!session || !conversation) return;
    const refreshMessages = async () => {
      const response = await fetch(`${API_URL}/api/conversations/${conversation.id}/messages?sessionToken=${encodeURIComponent(session.token)}`);
      if (response.ok) setMessages((await response.json()).messages);
    };
    const timer = setInterval(() => void refreshMessages(), 5000);
    return () => clearInterval(timer);
  }, [session, conversation]);

  async function sendMessage() {
    if (!session || !conversation || !messageText.trim()) return;
    const originalText = messageText.trim();
    setMessageText('');
    try {
      const response = await fetch(`${API_URL}/api/conversations/${conversation.id}/messages`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionToken: session.token, originalText, sourceLocale: 'en', targetLocale: 'vi' }) });
      if (!response.ok) throw new Error('Could not send message');
      const message: ChatMessage = await response.json();
      setMessages(current => [...current, message]);
    } catch (caught) { setMessageText(originalText); Alert.alert('Message failed', caught instanceof Error ? caught.message : 'Could not send message'); }
  }

  const activeOrders = useMemo(() => orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status)), [orders]);

  return <SafeAreaView style={styles.safe}><ScrollView contentContainerStyle={styles.container}>
    <Text style={styles.eyebrow}>HOTEL BRIDGE · MOBILE</Text>
    <Text style={styles.title}>Your stay, made simple.</Text>
    <Text style={styles.subtitle}>Request hotel services and chat with the hotel from your phone.</Text>

    {!session ? <View style={styles.card}><Text style={styles.heading}>{restoring ? 'Restoring your stay…' : 'Start your stay'}</Text><Text style={styles.label}>Room number</Text><TextInput value={roomNumber} onChangeText={setRoomNumber} keyboardType="number-pad" placeholder="302" style={styles.input} /><Pressable style={styles.primary} onPress={() => void startStay()} disabled={loading || restoring || !roomNumber.trim()}><Text style={styles.primaryText}>{restoring || loading ? 'Connecting…' : 'Enter hotel app'}</Text></Pressable>{error ? <Text style={styles.error}>{error}</Text> : null}<Text style={styles.hint}>Deep link example: hotelbridge://room/302. Sessions are stored securely on this device until they expire.</Text></View> : <>
      <View style={styles.sessionBar}><Text style={styles.sessionText}>Room {session.roomNumber}</Text><Text style={styles.live}>● Connected</Text></View>
      <Text style={styles.sectionTitle}>Hotel services</Text>
      {loading ? <ActivityIndicator /> : services.map(service => <View style={styles.service} key={service.id}><View style={styles.serviceCopy}><Text style={styles.serviceName}>{service.name}</Text><Text style={styles.serviceMeta}>{service.localizedName} · {service.etaMinutes} min</Text><Text style={styles.price}>{service.priceLabel}</Text></View><Pressable style={styles.secondary} onPress={() => void requestService(service)}><Text style={styles.secondaryText}>Request</Text></Pressable></View>)}
      <View style={styles.requestsHeader}><Text style={styles.sectionTitle}>My requests</Text><Text style={styles.count}>{activeOrders.length} active</Text></View>
      {orders.length === 0 ? <Text style={styles.empty}>Your requests will appear here.</Text> : orders.map(order => <View style={styles.order} key={order.id}><View><Text style={styles.serviceName}>{order.serviceId}</Text><Text style={styles.serviceMeta}>{order.id} · Due {new Date(order.dueAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text></View><Text style={styles.status}>{statusLabel(order.status)}</Text></View>)}
      <Text style={styles.sectionTitle}>Chat with the hotel</Text>
      <View style={styles.chatCard}>
        {chatLoading ? <ActivityIndicator /> : messages.length === 0 ? <Text style={styles.empty}>Ask the front desk for help.</Text> : messages.map(message => <View style={[styles.message, message.sender === 'guest' ? styles.guestMessage : styles.staffMessage]} key={message.id}><Text style={styles.messageSender}>{message.sender === 'guest' ? 'You' : 'Hotel staff'}</Text><Text style={styles.messageText}>{message.originalText}</Text>{message.translatedText !== message.originalText ? <Text style={styles.translation}>{message.translatedText}</Text> : null}</View>)}
        <View style={styles.composer}><TextInput value={messageText} onChangeText={setMessageText} placeholder="Write a message…" multiline style={styles.messageInput} /><Pressable style={styles.send} onPress={() => void sendMessage()} disabled={!conversation || !messageText.trim()}><Text style={styles.sendText}>Send</Text></Pressable></View>
        <Text style={styles.demoNote}>Translations are labelled demo output until a provider is connected.</Text>
      </View>
    </>}
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#f5f6f1' }, container: { padding: 24, gap: 16 }, eyebrow: { color: '#617269', fontSize: 11, fontWeight: '700', letterSpacing: 1.5 }, title: { color: '#14251f', fontSize: 36, fontWeight: '700', marginTop: 8 }, subtitle: { color: '#617269', fontSize: 16, lineHeight: 24 }, card: { backgroundColor: '#fff', borderRadius: 16, padding: 20, gap: 12, marginTop: 12 }, heading: { color: '#14251f', fontSize: 22, fontWeight: '700' }, label: { color: '#617269', fontSize: 13, fontWeight: '600' }, input: { borderColor: '#dce2dc', borderWidth: 1, borderRadius: 8, padding: 14, fontSize: 18, color: '#14251f' }, primary: { backgroundColor: '#14251f', borderRadius: 8, padding: 15, alignItems: 'center' }, primaryText: { color: '#fff', fontWeight: '700' }, hint: { color: '#8a958e', fontSize: 12, lineHeight: 18 }, error: { color: '#b34d42', fontSize: 13 }, sessionBar: { backgroundColor: '#dce9d7', borderRadius: 10, padding: 14, flexDirection: 'row', justifyContent: 'space-between' }, sessionText: { color: '#14251f', fontWeight: '700' }, live: { color: '#347047', fontSize: 13 }, sectionTitle: { color: '#14251f', fontSize: 24, fontWeight: '700', marginTop: 8 }, service: { backgroundColor: '#fff', borderRadius: 14, padding: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }, serviceCopy: { flex: 1, gap: 4 }, serviceName: { color: '#14251f', fontSize: 16, fontWeight: '700' }, serviceMeta: { color: '#74807a', fontSize: 12 }, price: { color: '#617269', fontSize: 12, fontWeight: '600' }, secondary: { borderColor: '#14251f', borderWidth: 1, borderRadius: 8, paddingVertical: 10, paddingHorizontal: 12 }, secondaryText: { color: '#14251f', fontWeight: '700' }, requestsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }, count: { color: '#617269', fontSize: 13 }, empty: { color: '#74807a' }, order: { backgroundColor: '#fff', borderRadius: 12, padding: 15, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, status: { color: '#347047', fontWeight: '700', fontSize: 12 }, chatCard: { backgroundColor: '#fff', borderRadius: 14, padding: 14, gap: 10 }, message: { borderRadius: 10, padding: 12, maxWidth: '92%', gap: 4 }, guestMessage: { backgroundColor: '#e7f0e3', alignSelf: 'flex-end' }, staffMessage: { backgroundColor: '#f0f2ef', alignSelf: 'flex-start' }, messageSender: { color: '#617269', fontSize: 11, fontWeight: '700' }, messageText: { color: '#14251f', fontSize: 15, lineHeight: 21 }, translation: { color: '#617269', fontSize: 13, fontStyle: 'italic', lineHeight: 18 }, composer: { flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: 4 }, messageInput: { flex: 1, minHeight: 44, maxHeight: 100, borderColor: '#dce2dc', borderWidth: 1, borderRadius: 8, padding: 10, color: '#14251f' }, send: { backgroundColor: '#14251f', borderRadius: 8, paddingVertical: 13, paddingHorizontal: 15 }, sendText: { color: '#fff', fontWeight: '700' }, demoNote: { color: '#8a958e', fontSize: 11, lineHeight: 16 } });

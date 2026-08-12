import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { GuestSession, Order, Service } from '@hotel-bridge/shared-types';

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000';

function statusLabel(status: Order['status']) {
  return status.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, letter => letter.toUpperCase());
}

export default function GuestMobileHome() {
  const [roomNumber, setRoomNumber] = useState('302');
  const [session, setSession] = useState<GuestSession | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function startStay() {
    setLoading(true); setError('');
    try {
      const sessionResponse = await fetch(`${API_URL}/api/guest-sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ roomNumber, locale: 'en' }) });
      if (!sessionResponse.ok) throw new Error('Could not start room session');
      const active: GuestSession = await sessionResponse.json();
      const servicesResponse = await fetch(`${API_URL}/api/services`);
      if (!servicesResponse.ok) throw new Error('Could not load hotel services');
      setSession(active); setServices((await servicesResponse.json()).services);
      setOrders([]);
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
    const refresh = async () => {
      const response = await fetch(`${API_URL}/api/orders?sessionToken=${encodeURIComponent(session.token)}`);
      if (response.ok) setOrders((await response.json()).orders);
    };
    const timer = setInterval(() => void refresh(), 5000);
    return () => clearInterval(timer);
  }, [session]);

  const activeOrders = useMemo(() => orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status)), [orders]);

  return <SafeAreaView style={styles.safe}><ScrollView contentContainerStyle={styles.container}>
    <Text style={styles.eyebrow}>HOTEL BRIDGE · MOBILE</Text>
    <Text style={styles.title}>Your stay, made simple.</Text>
    <Text style={styles.subtitle}>Request hotel services directly from your phone.</Text>

    {!session ? <View style={styles.card}><Text style={styles.heading}>Start your stay</Text><Text style={styles.label}>Room number</Text><TextInput value={roomNumber} onChangeText={setRoomNumber} keyboardType="number-pad" placeholder="302" style={styles.input} /><Pressable style={styles.primary} onPress={() => void startStay()} disabled={loading || !roomNumber.trim()}><Text style={styles.primaryText}>{loading ? 'Connecting…' : 'Enter hotel app'}</Text></Pressable>{error ? <Text style={styles.error}>{error}</Text> : null}<Text style={styles.hint}>For local testing on Android emulator, the API defaults to 10.0.2.2:8000.</Text></View> : <>
      <View style={styles.sessionBar}><Text style={styles.sessionText}>Room {session.roomNumber}</Text><Text style={styles.live}>● Connected</Text></View>
      <Text style={styles.sectionTitle}>Hotel services</Text>
      {loading ? <ActivityIndicator /> : services.map(service => <View style={styles.service} key={service.id}><View style={styles.serviceCopy}><Text style={styles.serviceName}>{service.name}</Text><Text style={styles.serviceMeta}>{service.localizedName} · {service.etaMinutes} min</Text><Text style={styles.price}>{service.priceLabel}</Text></View><Pressable style={styles.secondary} onPress={() => void requestService(service)}><Text style={styles.secondaryText}>Request</Text></Pressable></View>)}
      <View style={styles.requestsHeader}><Text style={styles.sectionTitle}>My requests</Text><Text style={styles.count}>{activeOrders.length} active</Text></View>
      {orders.length === 0 ? <Text style={styles.empty}>Your requests will appear here.</Text> : orders.map(order => <View style={styles.order} key={order.id}><View><Text style={styles.serviceName}>{order.serviceId}</Text><Text style={styles.serviceMeta}>{order.id} · Due {new Date(order.dueAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</Text></View><Text style={styles.status}>{statusLabel(order.status)}</Text></View>)}
    </>}
  </ScrollView></SafeAreaView>;
}

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#f5f6f1' }, container: { padding: 24, gap: 16 }, eyebrow: { color: '#617269', fontSize: 11, fontWeight: '700', letterSpacing: 1.5 }, title: { color: '#14251f', fontSize: 36, fontWeight: '700', marginTop: 8 }, subtitle: { color: '#617269', fontSize: 16, lineHeight: 24 }, card: { backgroundColor: '#fff', borderRadius: 16, padding: 20, gap: 12, marginTop: 12 }, heading: { color: '#14251f', fontSize: 22, fontWeight: '700' }, label: { color: '#617269', fontSize: 13, fontWeight: '600' }, input: { borderColor: '#dce2dc', borderWidth: 1, borderRadius: 8, padding: 14, fontSize: 18, color: '#14251f' }, primary: { backgroundColor: '#14251f', borderRadius: 8, padding: 15, alignItems: 'center' }, primaryText: { color: '#fff', fontWeight: '700' }, hint: { color: '#8a958e', fontSize: 12, lineHeight: 18 }, error: { color: '#b34d42', fontSize: 13 }, sessionBar: { backgroundColor: '#dce9d7', borderRadius: 10, padding: 14, flexDirection: 'row', justifyContent: 'space-between' }, sessionText: { color: '#14251f', fontWeight: '700' }, live: { color: '#347047', fontSize: 13 }, sectionTitle: { color: '#14251f', fontSize: 24, fontWeight: '700', marginTop: 8 }, service: { backgroundColor: '#fff', borderRadius: 14, padding: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }, serviceCopy: { flex: 1, gap: 4 }, serviceName: { color: '#14251f', fontSize: 16, fontWeight: '700' }, serviceMeta: { color: '#74807a', fontSize: 12 }, price: { color: '#617269', fontSize: 12, fontWeight: '600' }, secondary: { borderColor: '#14251f', borderWidth: 1, borderRadius: 8, paddingVertical: 10, paddingHorizontal: 12 }, secondaryText: { color: '#14251f', fontWeight: '700' }, requestsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }, count: { color: '#617269', fontSize: 13 }, empty: { color: '#74807a' }, order: { backgroundColor: '#fff', borderRadius: 12, padding: 15, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }, status: { color: '#347047', fontWeight: '700', fontSize: 12 } });

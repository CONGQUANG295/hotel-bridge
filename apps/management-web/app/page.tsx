'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Order, OrderStatus, StaffRole } from '@hotel-bridge/shared-types';

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
const role: StaffRole = 'front_desk';
const labels: Record<OrderStatus, string> = {
  NEW: 'New request', ACCEPTED: 'Accepted', IN_PROGRESS: 'In progress', READY: 'Ready',
  DELIVERED: 'Delivered', COMPLETED: 'Completed', CANCELLED: 'Cancelled', ESCALATED: 'Escalated',
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat('en', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export default function ManagementHome() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadOrders() {
    try {
      setError('');
      const response = await fetch(`${API_URL}/api/management/inbox`, { headers: { 'X-Staff-Role': role }, cache: 'no-store' });
      if (!response.ok) throw new Error('Could not load the operations inbox');
      const data = await response.json();
      setOrders(data.orders);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load the operations inbox');
    } finally { setLoading(false); }
  }

  useEffect(() => { void loadOrders(); }, []);

  async function updateStatus(orderId: string, status: OrderStatus) {
    const response = await fetch(`${API_URL}/api/orders/${orderId}/events`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Staff-Role': role }, body: JSON.stringify({ status }),
    });
    if (!response.ok) { setError('Status update failed'); return; }
    const changed: Order = await response.json();
    setOrders(current => current.map(order => order.id === changed.id ? changed : order));
  }

  const openOrders = useMemo(() => orders.filter(order => !['COMPLETED', 'CANCELLED'].includes(order.status)), [orders]);
  const escalations = orders.filter(order => order.status === 'ESCALATED').length;

  return <main className="management-shell"><aside><strong>Hotel Bridge</strong><p className="muted">Management</p><nav><a className="active">Inbox</a><a>Orders</a><a>Escalations</a><a>Services</a><a>Staff</a></nav><small>Signed in as Linh · Front desk</small></aside><section className="dashboard"><header><div><p className="eyebrow">OPERATIONS · TODAY</p><h1>Good morning, Linh.</h1></div><button>All departments⌄</button></header><div className="stats"><article><span>Open requests</span><strong>{openOrders.length}</strong><small>Live from API</small></article><article><span>Total requests</span><strong>{orders.length}</strong><small>Persisted in SQLite</small></article><article><span>Escalations</span><strong>{escalations}</strong><small className="warning">Needs attention</small></article></div><section className="panel"><div className="panel-heading"><div><p className="eyebrow">INBOX</p><h2>Requests needing attention</h2></div><button className="light" onClick={() => void loadOrders()}>Refresh ↻</button></div>{error && <p role="alert" className="warning">{error}</p>}{loading ? <p>Loading inbox…</p> : orders.length === 0 ? <p>No orders yet. New guest requests will appear here.</p> : <div className="table">{orders.map(order => <div className="row" key={order.id}><div><strong>{order.serviceId}</strong><span>Room {order.roomNumber} · {order.id}</span></div><span className="department">{order.assignedRole}</span><span>{formatTime(order.dueAt)}</span><select aria-label={`Update ${order.id}`} value={order.status} onChange={event => void updateStatus(order.id, event.target.value as OrderStatus)}>{Object.entries(labels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>)}</div>}</section></section></main>;
}

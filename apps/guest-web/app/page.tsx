'use client';
import { useState } from 'react';
import type { Service } from '@hotel-bridge/shared-types';

const services: Service[] = [
  { id: 'towels', name: 'Extra towels', localizedName: 'Thêm khăn tắm', department: 'housekeeping', etaMinutes: 15, priceLabel: 'Complimentary' },
  { id: 'room-service', name: 'Room service', localizedName: 'Đồ ăn tại phòng', department: 'restaurant', etaMinutes: 35, priceLabel: 'From $8' },
  { id: 'maintenance', name: 'Room maintenance', localizedName: 'Báo hỏng thiết bị', department: 'maintenance', etaMinutes: 20, priceLabel: 'Complimentary' },
];

export default function GuestHome() {
  const [locale, setLocale] = useState('en');
  const [requested, setRequested] = useState<string[]>([]);
  return <main className="guest-shell"><header><strong>Hotel Bridge</strong><span>Room 302 · <select value={locale} onChange={event => setLocale(event.target.value)}><option value="en">English</option><option value="vi">Tiếng Việt</option></select></span></header><section className="hero"><p className="eyebrow">NO DOWNLOAD REQUIRED</p><h1>{locale === 'vi' ? 'Kỳ nghỉ đơn giản hơn.' : 'Your stay, made simple.'}</h1><p>Scan, choose your language, chat with the hotel, or request a service directly from your room.</p><div className="actions"><button onClick={() => document.getElementById('services')?.scrollIntoView()}>Browse services</button><button className="secondary">Chat with the hotel</button></div></section><section id="services"><div className="section-heading"><div><p className="eyebrow">AT YOUR SERVICE</p><h2>Hotel services</h2></div><span>{requested.length} requests</span></div><div className="service-grid">{services.map(service => <article className="service-card" key={service.id}><div><h3>{service.name}</h3><p>{service.localizedName}</p></div><footer><span>{service.priceLabel} · {service.etaMinutes} min</span><button onClick={() => setRequested(current => current.includes(service.id) ? current : [...current, service.id])}>{requested.includes(service.id) ? 'Requested ✓' : 'Request'}</button></footer></article>)}</div></section><section className="chat-card"><p className="eyebrow">MULTILINGUAL SUPPORT</p><h2>Need help in your language?</h2><p>Your original message and the hotel translation stay visible together for clarity.</p><button className="secondary">Start a conversation →</button></section></main>;
}

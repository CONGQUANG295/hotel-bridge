export const supportedLocales = ['en', 'vi', 'ja', 'ko', 'zh'] as const;
export type SupportedLocale = typeof supportedLocales[number];
export const copy = {
  en: { guestTitle: 'Your stay, made simple.', services: 'Hotel services', chat: 'Chat with the hotel', orders: 'My orders' },
  vi: { guestTitle: 'Kỳ nghỉ đơn giản hơn.', services: 'Dịch vụ khách sạn', chat: 'Chat với khách sạn', orders: 'Đơn của tôi' }
} as const;

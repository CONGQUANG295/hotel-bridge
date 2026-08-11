export type StaffRole = 'front_desk' | 'housekeeping' | 'restaurant' | 'maintenance' | 'manager';
export type OrderStatus = 'NEW' | 'ACCEPTED' | 'IN_PROGRESS' | 'READY' | 'DELIVERED' | 'COMPLETED' | 'CANCELLED' | 'ESCALATED';

export interface Service { id: string; name: string; localizedName: string; department: StaffRole; etaMinutes: number; priceLabel: string; }
export interface GuestSession { token: string; roomNumber: string; locale: string; expiresAt: string; }
export interface Order { id: string; roomNumber: string; serviceId: string; status: OrderStatus; quantity: number; note: string; dueAt: string; assignedRole: StaffRole; createdAt: string; updatedAt: string; }
export interface StaffUser { id: string; displayName: string; role: StaffRole; department: string; }
export interface ApiError { code: string; message: string; }

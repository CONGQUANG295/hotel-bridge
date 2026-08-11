import { Link } from 'expo-router';
import { SafeAreaView, Text, View } from 'react-native';

export default function GuestMobileHome() {
  return <SafeAreaView><View style={{padding: 24, gap: 16}}><Text style={{fontSize: 32, fontWeight: '700'}}>Hotel Bridge</Text><Text>Guest mobile companion for returning guests.</Text><Link href="/services">Browse hotel services →</Link></View></SafeAreaView>;
}

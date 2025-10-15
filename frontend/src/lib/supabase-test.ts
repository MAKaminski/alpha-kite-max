import { supabase } from './supabase';

export async function testSupabaseConnection(): Promise<boolean> {
  try {
    // Simple test query - will fail gracefully if no credentials
    const { error } = await supabase.from('equity_data').select('count', { count: 'exact', head: true });
    
    if (error) {
      console.error('Supabase connection test failed:', error.message);
      return false;
    }
    
    console.log('Supabase connection successful');
    return true;
  } catch (err) {
    console.error('Supabase connection error:', err);
    return false;
  }
}


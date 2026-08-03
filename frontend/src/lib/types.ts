export type User = {
  id: number
  name: string
  email: string
  created_at: string
}

export type LostItem = {
  id: number
  user_id: number
  item_name: string
  category: string
  description: string
  date_lost: string
  location: string
  image_path?: string | null
  image_url?: string | null
  status: string
  created_at: string
}

export type PublicLostItem = {
  id: number
  item_name: string
  category: string
  description: string
  date_lost: string
  location: string
  image_url?: string | null
  status: string
  created_at: string
}

export type FoundItem = {
  id: number
  user_id: number
  description: string
  category: string
  date_found: string
  location: string
  image_path?: string | null
  image_url?: string | null
  status: string
  created_at: string
}

export type Match = {
  id: number
  text_score: number
  image_score?: number | null
  final_score: number
  status: 'pending' | 'confirmed' | 'rejected'
  created_at: string
  lost_item: LostItem
  found_item: FoundItem
}

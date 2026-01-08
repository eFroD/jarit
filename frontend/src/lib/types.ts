// src/lib/types.ts

export interface User {
  id: number;
  email: string;
  username: string;
  role: 'ADMIN' | 'USER';
  is_active: boolean;
  created_at: string;
}

export interface APIKey {
  id: number;
  service_name: string;
  base_url: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Author {
  '@type'?: string;
  name: string;
}

export interface HowToStep {
  '@type'?: string;
  text: string;
}

export interface HowToSection {
  name: string | null;
  itemListElement: HowToStep[];
}

export interface Recipe {
  '@context': string;
  '@type': string;
  name: string;
  description: string | null;
  image: string | string[] | null;
  recipeYield: string;
  recipeIngredient: string[];
  recipeInstructions: (HowToStep | HowToSection)[] | null;
  prepTime: string;
  cookTime: string;
  totalTime: string;
  recipeCategory: string;
  recipeCuisine: string;
  keywords: string[] | null;
  suitableForDiet: string;
  author: Author | null;
  video: string | null;
  url: string | null;
}

export interface RecipeError {
  error: string;
  missing_fields: string[];
}

export interface ExtractRecipeResponse {
  recipe: Recipe | null;
  suggested_version: Recipe | null;
  error_info: RecipeError;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterResponse {
  email: string;
  username: string;
  id: number;
  is_active: boolean;
  created_at: string;
}
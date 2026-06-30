/**
 * Presentational view-model types used by chart components.
 * Domain/data types now live in `@/lib/api` (backend-aligned).
 */

export interface TrendPoint {
  label: string;
  trust: number;
  tasks: number;
}

export interface CategoryScore {
  key: string;
  label: string;
  score: number;
  weight: number;
}

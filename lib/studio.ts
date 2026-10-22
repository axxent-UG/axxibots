export type StudioProduct = {
  slug: string;
  title: string;
  collection: string | null;
  status: string;
  price_eur: number | null;
  etsy_listing_id: number | null;
  section: string | null;
  product_type: string | null;
  owner_go_at: string | null;
  created_at: string;
  updated_at: string;
  error: string | null;
  downloads: number;
  images: number;
  assets_done: number;
  assets_total: number;
  art_eur: number;
};
export type Studio = {
  generated_at: string;
  products: StudioProduct[];
  budget: { today_eur: number; month_eur: number; day_cap_eur: number | null; month_cap_eur: number | null };
  legacy: { decisions_pending: number; org_proposals_open: number; tasks_open: number };
};
/** Plain-language meaning of each jj_kits status, in pipeline order. */
export const studioStages: [string, string][] = [
  ["art", "Illustrations"],
  ["assembling", "Assembling"],
  ["qa", "Waiting for your release"],
  ["ready", "Released, listing next"],
  ["listing", "Creating Etsy draft"],
  ["draft", "Etsy draft, ready to publish"],
];
export const demoStudio: Studio = {
  generated_at: new Date(0).toISOString(),
  products: [
    { slug: "demo-kit", title: "Demo Winter Ephemera Kit", collection: "Demo Winter", status: "qa", price_eur: 3.95, etsy_listing_id: null, section: "Christmas Ephemera", product_type: "Ephemera Kit", owner_go_at: null, created_at: new Date(0).toISOString(), updated_at: new Date(0).toISOString(), error: null, downloads: 3, images: 8, assets_done: 0, assets_total: 0, art_eur: 0 },
    { slug: "demo-tags", title: "Demo Winter Gift Tags", collection: "Demo Winter", status: "draft", price_eur: 2.19, etsy_listing_id: 1, section: "Tags & Labels", product_type: "Gift Tags", owner_go_at: null, created_at: new Date(0).toISOString(), updated_at: new Date(0).toISOString(), error: null, downloads: 3, images: 6, assets_done: 0, assets_total: 0, art_eur: 0 },
  ],
  budget: { today_eur: 0.4, month_eur: 3.2, day_cap_eur: 2, month_cap_eur: 15 },
  legacy: { decisions_pending: 0, org_proposals_open: 0, tasks_open: 0 },
};

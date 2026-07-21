export type Field = {
  label: string;
  value: string;
  unit?: string;
};

export type PropertyGroup = {
  title: string;
  properties: Field[];
};

export type ProductDocument = {
  id: string;
  title: string;
  type: string;
  action: "open" | "download";
  href: string;
};

export type ProductPassport = {
  aasId: string;
  name: string;
  manufacturer?: string;
  productType?: string;
  description?: string;
  imageUrl: string;
  imageAlt: string;
  highlights: Field[];
  nameplate: Field[];
  technicalData: PropertyGroup[];
  documents: ProductDocument[];
};

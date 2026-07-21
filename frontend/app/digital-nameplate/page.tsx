import { FieldList } from "@/components/field-list";
import { PageHeader } from "@/components/page-header";
import { getSelectedProduct } from "@/lib/product/product-api";

export default async function DigitalNameplatePage() {
  const product = await getSelectedProduct();
  return <div className="page"><PageHeader eyebrow={product.name} title="Digital Nameplate" description="Identification and manufacturer information for this product instance." /><section className="content-card"><div className="card-heading"><div><h2>Identification</h2><p>Standardized digital nameplate information</p></div><span className="standard-chip">IDTA 02006</span></div><FieldList fields={product.nameplate} /></section></div>;
}

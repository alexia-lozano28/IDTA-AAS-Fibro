import { FieldList } from "@/components/field-list";
import { PageHeader } from "@/components/page-header";
import { getSelectedProduct } from "@/lib/product/product-api";

export default async function TechnicalDataPage() {
  const product = await getSelectedProduct();
  return <div className="page"><PageHeader eyebrow={product.name} title="Technical Data" description="Key mechanical, drive, and operating properties grouped for quick reference." /><div className="group-grid">{product.technicalData.map((group) => <section className="content-card technical-group" key={group.title}><div className="card-heading"><h2>{group.title}</h2></div><FieldList fields={group.properties} /></section>)}</div></div>;
}

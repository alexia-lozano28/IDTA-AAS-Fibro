import { Icon } from "@/components/icons";
import { PageHeader } from "@/components/page-header";
import { getSelectedProduct } from "@/lib/product/product-api";

export default async function DocumentsPage() {
  const product = await getSelectedProduct();
  return <div className="page"><PageHeader eyebrow={product.name} title="Documents" description="Technical documentation and product resources associated with this passport." /><section className="content-card document-list">{product.documents.map((document) => <article className="document-row" key={document.id}><span className="document-icon"><Icon name="documents" /></span><div><h2>{document.title}</h2><p>{document.type}</p></div><a className="document-action" href={document.href} target="_blank" rel="noreferrer">{document.action === "open" ? "Open" : "Download"}<Icon name="arrow" /></a></article>)}</section></div>;
}

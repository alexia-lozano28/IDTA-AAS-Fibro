import Image from "next/image";
import Link from "next/link";
import { Icon } from "@/components/icons";
import { getSelectedProduct } from "@/lib/product/product-api";

export default async function OverviewPage() {
  const product = await getSelectedProduct();
  return (
    <div className="page overview-page">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Digital Product Passport</p>
          <h1>{product.name}</h1>
          {product.productType && <p className="product-type">{product.productType}</p>}
          {product.description && <p className="hero-description">{product.description}</p>}
          {product.manufacturer && <div className="manufacturer"><span>Manufactured by</span><strong>{product.manufacturer}</strong></div>}
          <div className="hero-actions"><Link className="primary-button" href="/technical-data">Explore technical data <Icon name="arrow" /></Link><Link className="secondary-button" href="/documents">View documents</Link></div>
        </div>
        <div className="product-visual"><Image src={product.imageUrl} alt={product.imageAlt} fill priority sizes="(max-width: 800px) 100vw, 45vw" /></div>
      </section>
      <section aria-labelledby="highlights-title">
        <div className="section-heading"><div><p className="eyebrow">At a glance</p><h2 id="highlights-title">Product identification</h2></div></div>
        <div className="highlight-grid">{product.highlights.map((item) => <article className="highlight-card" key={item.label}><span>{item.label}</span><strong>{item.value}</strong></article>)}</div>
      </section>
      <footer className="passport-id"><span className="status-dot" /><div><span>Asset Administration Shell</span><code>{product.aasId}</code></div></footer>
    </div>
  );
}

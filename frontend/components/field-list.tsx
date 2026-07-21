import type { Field } from "@/lib/product/types";

export function FieldList({ fields }: { fields: Field[] }) {
  return (
    <dl className="field-list">
      {fields.map((field) => (
        <div className="field-row" key={field.label}>
          <dt>{field.label}</dt>
          <dd>{field.value}{field.unit && <span className="unit"> {field.unit}</span>}</dd>
        </div>
      ))}
    </dl>
  );
}

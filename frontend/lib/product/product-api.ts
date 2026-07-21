import { readFile } from "node:fs/promises";
import path from "node:path";
import type { Field, ProductDocument, ProductPassport, PropertyGroup } from "./types";

/**
 * Single product-data boundary for the UI. Every displayed product value is
 * mapped from the generated AAS environment. Replace readEnvironment() with
 * BaSyx discovery/repository calls later; page components need no changes.
 */
export async function getSelectedProduct(): Promise<ProductPassport> {
  const environment = await readEnvironment();
  const shell = environment.assetAdministrationShells?.[0];
  if (!shell?.id) throw new Error("The AAS environment contains no shell");

  const nameplate = findSubmodel(environment, "DigitalNameplate");
  const technical = findSubmodel(environment, "TechnicalData");
  const handover = findSubmodel(environment, "HandoverDocumentation");

  const name = requiredValue(nameplate, "ManufacturerProductDesignation");
  const manufacturer = valueAt(nameplate, "ManufacturerName");
  const technicalDesignation = valueAt(
    technical,
    "GeneralInformation",
    "ManufacturerProductDesignation",
  );
  const imageNote = valueAt(
    technical,
    "GeneralInformation",
    "ProductImages",
    0,
    "ImageNote",
  );

  const nameplateFields = fieldsFromPaths(nameplate, [
    ["Product URI", "URIOfTheProduct"],
    ["Manufacturer", "ManufacturerName"],
    ["Product designation", "ManufacturerProductDesignation"],
    ["Manufacturer order code", "OrderCodeOfManufacturer"],
    ["Manufacturer article number", "ProductArticleNumberOfManufacturer"],
    ["Serial number", "SerialNumber"],
    ["Year of construction", "YearOfConstruction"],
    ["Date of manufacture", "DateOfManufacture"],
    ["Hardware version", "HardwareVersion"],
    ["Firmware version", "FirmwareVersion"],
    ["Software version", "SoftwareVersion"],
    ["Country of origin", "CountryOfOrigin"],
    ["Facility identifier", "UniqueFacilityIdentifier"],
  ]);

  const technicalData = [
    groupFromPaths("General information", technical, [
      ["Manufacturer", "GeneralInformation", "ManufacturerName"],
      ["Product designation", "GeneralInformation", "ManufacturerProductDesignation"],
      ["Manufacturer article number", "GeneralInformation", "ManufacturerArticleNumber"],
      ["Manufacturer order code", "GeneralInformation", "ManufacturerOrderCode"],
      ["Product image note", "GeneralInformation", "ProductImages", 0, "ImageNote"],
    ]),
    groupFromPaths("Product classification", technical, [
      ["Classification system", "ProductClassifications", 0, "ClassificationSystem"],
      ["Classification system version", "ProductClassifications", 0, "ClassificationSystemVersion"],
      ["Classification system URL", "ProductClassifications", 0, "ClassificationSystemUrl"],
      ["Product class ID", "ProductClassifications", 0, "ProductClassId"],
      ["Product class coded name", "ProductClassifications", 0, "ProductClassCodedName"],
      ["Product class name", "ProductClassifications", 0, "ProductClassName"],
    ]),
    groupFromElements(
      "Technical properties",
      elementAt(technical, "TechnicalPropertyAreas"),
    ),
    groupFromPaths("Further information", technical, [
      ["Valid date", "FurtherInformation", "ValidDate"],
    ]),
  ].filter((group): group is PropertyGroup => group !== undefined);

  const highlights = fieldsFromPaths(nameplate, [
    ["Article number", "ProductArticleNumberOfManufacturer"],
    ["Serial number", "SerialNumber"],
    ["Manufactured", "DateOfManufacture"],
    ["Country of origin", "CountryOfOrigin"],
  ]);

  return {
    aasId: shell.id,
    name,
    manufacturer,
    productType:
      technicalDesignation && technicalDesignation !== name
        ? technicalDesignation
        : undefined,
    imageUrl: "/product.webp",
    imageAlt: imageNote ?? name,
    highlights,
    nameplate: nameplateFields,
    technicalData,
    documents: mapDocuments(handover),
  };
}

type AasElement = {
  id?: string;
  idShort?: string;
  modelType?: string;
  contentType?: string;
  displayName?: Array<{ language?: string; text?: string }>;
  submodelElements?: AasElement[];
  value?: unknown;
};

type AasEnvironment = {
  assetAdministrationShells?: AasElement[];
  submodels?: AasElement[];
};

type ValuePath = [label: string, ...path: Array<string | number>];

async function readEnvironment(): Promise<AasEnvironment> {
  const configured = process.env.AAS_ENVIRONMENT_PATH;
  const candidates = [
    configured,
    path.resolve(process.cwd(), "data/generated/final_basyx_aas_environment.json"),
    path.resolve(process.cwd(), "../data/generated/final_basyx_aas_environment.json"),
  ].filter((candidate): candidate is string => Boolean(candidate));

  for (const candidate of candidates) {
    try {
      return JSON.parse(await readFile(candidate, "utf8")) as AasEnvironment;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    }
  }
  throw new Error(`AAS environment not found. Checked: ${candidates.join(", ")}`);
}

function findSubmodel(environment: AasEnvironment, idShort: string): AasElement {
  const submodel = environment.submodels?.find((item) => item.idShort === idShort);
  if (!submodel) throw new Error(`Required submodel ${idShort} is missing`);
  return { ...submodel, value: submodel.submodelElements };
}

function childAt(element: AasElement, segment: string | number): AasElement | undefined {
  if (!Array.isArray(element.value)) return undefined;
  if (typeof segment === "number") return element.value[segment] as AasElement | undefined;
  return (element.value as AasElement[]).find((child) => child.idShort === segment);
}

function elementAt(root: AasElement, ...segments: Array<string | number>): AasElement | undefined {
  let current: AasElement | undefined = root;
  for (const segment of segments) {
    if (!current) return undefined;
    current = childAt(current, segment);
  }
  return current;
}

function valueAt(root: AasElement, ...segments: Array<string | number>): string | undefined {
  const element = elementAt(root, ...segments);
  if (!element) return undefined;
  const raw = element.value;
  if (typeof raw === "string" || typeof raw === "number" || typeof raw === "boolean") {
    return cleanValue(String(raw));
  }
  if (Array.isArray(raw)) {
    const languageValue = (raw as Array<{ language?: string; text?: string }>).find(
      (item) => item.language === "en" && typeof item.text === "string",
    ) ?? (raw as Array<{ text?: string }>).find((item) => typeof item.text === "string");
    return languageValue?.text ? cleanValue(languageValue.text) : undefined;
  }
  return undefined;
}

function cleanValue(value: string): string | undefined {
  const cleaned = value.trim().replace(/@(en|de)$/i, "").trim();
  if (!cleaned || /^n\/a(?:\s|$)/i.test(cleaned) || /^to be confirmed[.]?$/i.test(cleaned)) {
    return undefined;
  }
  if (/^ProductClassifications__\d+__$/.test(cleaned)) return undefined;
  return cleaned;
}

function requiredValue(root: AasElement, ...segments: Array<string | number>): string {
  const value = valueAt(root, ...segments);
  if (!value) throw new Error(`Required AAS value is missing: ${segments.join("/")}`);
  return value;
}

function fieldsFromPaths(root: AasElement, paths: ValuePath[]): Field[] {
  return paths.flatMap(([label, ...segments]) => {
    const value = valueAt(root, ...segments);
    return value ? [{ label, value }] : [];
  });
}

function groupFromPaths(title: string, root: AasElement, paths: ValuePath[]): PropertyGroup | undefined {
  const properties = fieldsFromPaths(root, paths);
  return properties.length ? { title, properties } : undefined;
}

function groupFromElements(
  title: string,
  root: AasElement | undefined,
): PropertyGroup | undefined {
  if (!root) return undefined;
  const properties: Field[] = [];
  collectLeafFields(root, properties);
  return properties.length ? { title, properties } : undefined;
}

function collectLeafFields(element: AasElement, fields: Field[]): void {
  if (Array.isArray(element.value)) {
    const languageValue = (element.value as Array<{ language?: string; text?: string }>).find(
      (item) => item.language === "en" && typeof item.text === "string",
    );
    if (languageValue?.text) {
      const value = cleanValue(languageValue.text);
      if (value) fields.push({ label: elementLabel(element), value });
      return;
    }
    for (const child of element.value as AasElement[]) {
      if (child && typeof child === "object") collectLeafFields(child, fields);
    }
    return;
  }
  if (
    typeof element.value === "string"
    || typeof element.value === "number"
    || typeof element.value === "boolean"
  ) {
    const value = cleanValue(String(element.value));
    if (value) fields.push({ label: elementLabel(element), value });
  }
}

function elementLabel(element: AasElement): string {
  return element.displayName?.find(
    (name) => name.language === "en" && name.text,
  )?.text ?? element.idShort ?? "Workbook value";
}

function mapDocuments(handover: AasElement): ProductDocument[] {
  const documents = elementAt(handover, "Documents")?.value;
  if (!Array.isArray(documents)) return [];
  return (documents as AasElement[]).flatMap((document, index) => {
    const title = valueAt(document, "DocumentVersions", 0, "Title");
    const href = valueAt(document, "DocumentVersions", 0, "DigitalFiles", 0);
    const type = valueAt(document, "DocumentClassifications", 0, "ClassName");
    if (!title || !href || !type) return [];
    return [{
      id: valueAt(document, "DocumentIds", 0, "DocumentIdentifier") ?? `${href}-${index}`,
      title,
      type,
      action: href.toLowerCase().endsWith(".pdf") ? "open" : "download",
      href,
    }];
  });
}

import { slugify } from "./slugify";
import type { Property } from "@/lib/types/gis";

/**
 * Format a location string, handling null/undefined/invalid values
 * @param value - The value to format
 * @param fallback - Fallback value if location is empty
 * @returns Formatted location string
 */
const formatLocation = (
  value: string | null | undefined,
  fallback: string = "No location present"
): string => {
  if (!value) return fallback;
  const normalizedValue = value.toString().trim().toLowerCase();
  const emptyValues = [
    "",
    "null",
    "undefined",
    "n/a",
    "na",
    "none",
    "unknown",
    "not available",
    "not provided",
    "-",
    "0",
  ];
  return emptyValues.includes(normalizedValue) ? fallback : value;
};

/**
 * Build a canonical URL for a property that matches the texasparcels.com format
 * @param property - The property object from the catalog
 * @returns The full URL to the property on texasparcels.com
 */
export const buildPropertyUrl = (property: Property): string | null => {
  // We need at least a doc_id and county to build a URL
  if (!property.doc_id || !property.county) {
    return null;
  }

  const state = "tx";
  
  // Handle county
  const county =
    property.county && property.county.trim().length !== 0
      ? slugify(property.county.toLowerCase().replace(/\s+/g, "-"))
      : "county-slug";

  // Handle city - the dashboard properties don't have a city field in the modal,
  // so we'll extract from situs_addr if possible, or use a default
  let city = "city-slug";
  if (property.situs_addr) {
    // Try to extract city from address (this is a best-effort approach)
    // Most addresses don't have city in situs_addr, so we'll use a default
    city = "city-slug";
  }

  // Build title from acreage and county
  const acreageStr = property.acreage
    ? String(property.acreage).replace(".", "-")
    : "unknown";
  
  const countyForTitle = formatLocation(property.county).toLowerCase();
  const title = `${acreageStr}-acres-in-${countyForTitle}`;
  
  const slug = slugify(title);
  const id = property.doc_id;

  // Build the full URL
  const url = `/land/${state}/${county}-county/${city}-city/${slug}-${id}`;
  
  // Return the full URL with domain
  return `https://texasparcels.com${url}`;
};

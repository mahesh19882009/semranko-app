import locationCatalog from './locations.json' with { type: 'json' };

// Thin frontend adapter over the canonical shared catalog.
export const KEYWORD_LOCATION_CATALOG = locationCatalog;
export const COUNTRY_LOCATION_CODES = Object.fromEntries(
  locationCatalog.map(({ name, locationCode }) => [name, locationCode])
);
export const COUNTRIES = locationCatalog.map(({ name, locationCode }) => ({
  label: name,
  value: name,
  code: locationCode,
}));

const sameLocationName = (left, right) => (
  Boolean(left && right && String(left).trim().toLowerCase() === String(right).trim().toLowerCase())
);

export function getCountryCode(country) {
  return COUNTRY_LOCATION_CODES[country] || 2840;
}

export function getCountries() {
  return locationCatalog;
}

export function getStates(country) {
  return locationCatalog.find((entry) => sameLocationName(entry.name, country))?.states || [];
}

export function getCities(country, state) {
  return getStates(country).find((entry) => sameLocationName(entry.name, state))?.cities || [];
}

export function resolveKeywordLocation({ country, state = null, city = null, locationCode = null } = {}) {
  if (!country) throw new Error('Country is required');
  const countryEntry = locationCatalog.find((entry) => sameLocationName(entry.name, country));
  if (!countryEntry) {
    return { country, state: null, city: null, locationCode: locationCode || getCountryCode(country), label: country };
  }

  let selected = countryEntry;
  let stateEntry = null;
  if (state) {
    stateEntry = countryEntry.states.find((entry) => sameLocationName(entry.name, state));
    if (!stateEntry) throw new Error(`State is not available for ${countryEntry.name}`);
    selected = stateEntry;
  }
  if (city) {
    if (!stateEntry) throw new Error('City requires a state');
    const cityEntry = stateEntry.cities.find((entry) => sameLocationName(entry.name, city));
    if (!cityEntry) throw new Error(`City is not available for ${stateEntry.name}`);
    selected = cityEntry;
  }

  return {
    country: countryEntry.name,
    state: state || null,
    city: city || null,
    locationCode: !state && !city && locationCode ? locationCode : selected.locationCode,
    label: [city, state, countryEntry.name].filter(Boolean).join(', '),
  };
}

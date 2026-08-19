export const COUNTRY_LOCATION_CODES = {
  "India": 2356,
  "United States": 2840,
  "United Kingdom": 2826,
  "Canada": 2124,
  "Australia": 2036,
  "Germany": 2276,
  "France": 2250,
  "Japan": 2392,
  "Brazil": 2076,
  "China": 2156,
  "Italy": 2380,
  "Spain": 2724,
  "Mexico": 2484,
  "South Korea": 2410,
  "Netherlands": 2450,
  "Saudi Arabia": 2682,
  "UAE": 2786,
  "Singapore": 2468,
  "Hong Kong": 2328,
};

export const COUNTRIES = Object.keys(COUNTRY_LOCATION_CODES).map((country) => ({
  label: country,
  value: country,
  code: COUNTRY_LOCATION_CODES[country],
}));

export function getCountryCode(country) {
  return COUNTRY_LOCATION_CODES[country] || 2840;
}

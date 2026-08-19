import { useState, useEffect } from "react";
import { COUNTRIES, getCountryCode } from "../data/locations";

export default function CountrySelector({ value = "India", onChange, disabled }) {
  const [country, setCountry] = useState(value || "India");

  useEffect(() => {
    if (value !== country) {
      setCountry(value || "India");
    }
  }, [value, country]);

  useEffect(() => {
    if (country !== value) {
      onChange(country);
    }
  }, [country, onChange, value]);

  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">Country</label>
      <select
        value={country}
        onChange={(e) => setCountry(e.target.value)}
        disabled={disabled}
        className="w-full h-[45px] rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none disabled:bg-slate-50 disabled:cursor-not-allowed"
      >
        {COUNTRIES.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>
    </div>
  );
}

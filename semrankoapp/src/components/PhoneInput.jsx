'use client'

import { useEffect, useMemo, useRef, useState } from 'react';
import {
  defaultCountries,
  FlagImage,
  parseCountry,
  usePhoneInput,
} from 'react-international-phone';

/**
 * Accessible international phone input. It uses the maintained library's
 * headless formatter and country metadata; the server remains authoritative
 * for validity and canonicalization.
 */
export default function PhoneInput({
  id = 'mobile',
  value,
  onChange,
  error,
  disabled = false,
  required = false,
}) {
  const [countryPickerOpen, setCountryPickerOpen] = useState(false);
  const [countryQuery, setCountryQuery] = useState('');
  const countrySearchRef = useRef(null);
  const countries = useMemo(() => defaultCountries.map(parseCountry), []);
  const {
    country,
    handlePhoneValueChange,
    inputRef,
    inputValue,
    setCountry,
  } = usePhoneInput({
    defaultCountry: 'in',
    value,
    disableDialCodeAndPrefix: true,
    onChange: ({ phone, country: selectedCountry }) => onChange?.({
      phone,
      country: selectedCountry.iso2.toUpperCase(),
    }),
  });
  const filteredCountries = countries.filter((candidate) => {
    const query = countryQuery.trim().toLowerCase();
    return !query
      || candidate.name.toLowerCase().includes(query)
      || candidate.dialCode.startsWith(query.replace(/^\+/, ''));
  });

  useEffect(() => {
    if (countryPickerOpen) countrySearchRef.current?.focus();
  }, [countryPickerOpen]);

  const selectCountry = (selectedCountry) => {
    setCountry(selectedCountry.iso2, { focusOnInput: true });
    setCountryQuery('');
    setCountryPickerOpen(false);
  };

  return (
    <div className="semranko-phone-field">
      <label htmlFor={id}>Mobile number</label>
      <div className="semranko-phone-control">
        <div className="semranko-phone-country-selector">
          <button
            type="button"
            className="semranko-phone-country-button"
            onClick={() => setCountryPickerOpen((open) => !open)}
            disabled={disabled}
            aria-label={`Country selector: ${country.name}, +${country.dialCode}`}
            aria-haspopup="listbox"
            aria-expanded={countryPickerOpen}
          >
            <FlagImage iso2={country.iso2} size={18} />
            <span>+{country.dialCode}</span>
            <span aria-hidden="true" className="mt-[-10px]">⌄</span>
          </button>
          {countryPickerOpen && (
            <div className="semranko-phone-country-dropdown" role="dialog" aria-label="Choose country">
              <input
                ref={countrySearchRef}
                type="search"
                className="semranko-phone-country-search"
                placeholder="Search country or code"
                value={countryQuery}
                onChange={(event) => setCountryQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Escape') setCountryPickerOpen(false);
                }}
              />
              <div className="semranko-phone-country-list" role="listbox" aria-label="Countries">
                {filteredCountries.map((candidate) => (
                  <button
                    key={candidate.iso2}
                    type="button"
                    role="option"
                    aria-selected={candidate.iso2 === country.iso2}
                    className="semranko-phone-country-option"
                    onClick={() => selectCountry(candidate)}
                  >
                    <FlagImage iso2={candidate.iso2} size={18} />
                    <span>{candidate.name}</span>
                    <span>+{candidate.dialCode}</span>
                  </button>
                ))}
                {!filteredCountries.length && <p className="semranko-phone-empty">No countries found.</p>}
              </div>
            </div>
          )}
        </div>
        <input
          ref={inputRef}
          id={id}
          name="mobile"
          type="tel"
          value={inputValue}
          onChange={handlePhoneValueChange}
          disabled={disabled}
          required={required}
          autoComplete="tel-national"
          inputMode="tel"
          placeholder="Mobile number"
          className="semranko-phone-number-input"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
        />
      </div>
      {error && <p id={`${id}-error`} className="semranko-phone-error">{error}</p>}
    </div>
  );
}

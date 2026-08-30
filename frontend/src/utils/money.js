/**
 * Shared money helpers for the Community Funding surface.
 *
 * All money is stored server-side as integer minor units (paise). These
 * helpers only convert for display/input; the server's integer minor units
 * are always the canonical representation. Floats never enter the money path.
 */

const MINOR_UNITS_PER_CURRENCY_UNIT = 100;

/**
 * Convert a user-entered rupee amount (string or number, decimals allowed down
 * to ₹0.01) to integer minor units (paise).
 *
 * Returns null for empty, non-finite, zero, negative, sub-paisa (e.g. ₹0.004)
 * or unsafe-integer results so callers can treat all of them as invalid.
 *
 * @param {string|number} value
 * @returns {number|null}
 */
export function rupeesToMinor(value) {
  if (value === null || value === undefined || String(value).trim() === "") {
    return null;
  }
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount <= 0) {
    return null;
  }
  const minor = Math.round(amount * MINOR_UNITS_PER_CURRENCY_UNIT);
  if (minor <= 0 || !Number.isSafeInteger(minor)) {
    return null;
  }
  return minor;
}

/**
 * Convert an integer minor-unit amount back to a decimal rupee string for
 * input fields (e.g. 50050 -> "500.5").
 * @param {number} minor
 */
export function minorToRupees(minor) {
  return String(Number(minor) / MINOR_UNITS_PER_CURRENCY_UNIT);
}

/**
 * Format an integer minor-unit amount (paise) as a currency string.
 * @param {number} minor
 * @param {string} [currency]
 */
export function formatMoney(minor, currency = "INR") {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(minor / MINOR_UNITS_PER_CURRENCY_UNIT);
  } catch {
    return `${minor} ${currency}`;
  }
}

const ISO_CURRENCY = /^[A-Z]{3}$/;

export function normaliseCurrency(value: unknown): string {
  return typeof value === "string" && ISO_CURRENCY.test(value) ? value : "USD";
}

export function formatMoneyMinor(valueMinor: number, currency: unknown, locale?: string): string {
  const code = normaliseCurrency(currency);
  return new Intl.NumberFormat(locale, {
    style: "currency",
    currency: code,
    currencyDisplay: "narrowSymbol",
    maximumFractionDigits: 2,
  }).format(valueMinor / 100);
}

export function formatMoneyMajor(value: number, currency: unknown, locale?: string): string {
  return formatMoneyMinor(Math.round(value * 100), currency, locale);
}

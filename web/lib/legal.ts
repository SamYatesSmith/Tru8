/**
 * Single source of truth for Trueight Ltd's legal identity.
 *
 * The company number, ICO registration and statutory contact details are
 * displayed across the legal pages (privacy, terms, cookie, refund). They live
 * here so a change on renewal is made in exactly one place.
 */
export const LEGAL = {
  companyName: 'Trueight Ltd',
  tradingName: 'Tru8',
  companyNumber: '17090683',
  icoRegistration: 'ZC110163',
  contactEmail: 'hello@trueight.com',
  location: 'London, UK',
} as const;

/** The UK Information Commissioner's Office — for complaint / supervisory-authority blocks. */
export const ICO = {
  name: "Information Commissioner's Office",
  addressLines: ['Wycliffe House, Water Lane', 'Wilmslow, Cheshire SK9 5AF'],
  website: 'ico.org.uk',
  websiteUrl: 'https://ico.org.uk',
} as const;

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
  /** Where the company is registered. Required alongside the number. */
  placeOfRegistration: 'England and Wales',
  /**
   * The REGISTERED OFFICE, not a description of where we work.
   *
   * Companies Act 2006 website-disclosure rules require the registered name,
   * company number, place of registration and registered office address. The
   * contact page previously said "Tru8 Ltd" / "London, UK" — a company that does
   * not exist at an address that is not the registered one. Verified against
   * Companies House 2026-08-03.
   */
  registeredOffice: '115a Queensway, Petts Wood, Orpington, England, BR5 1DG',
  icoRegistration: 'ZC110163',
  contactEmail: 'hello@trueight.com',
} as const;

/** The UK Information Commissioner's Office — for complaint / supervisory-authority blocks. */
export const ICO = {
  name: "Information Commissioner's Office",
  addressLines: ['Wycliffe House, Water Lane', 'Wilmslow, Cheshire SK9 5AF'],
  website: 'ico.org.uk',
  websiteUrl: 'https://ico.org.uk',
} as const;

/**
 * /compare demo data — one claim, Tru8 vs four grounding APIs.
 *
 * LIVE CAPTURES — all four callable APIs, same claim, same sitting,
 * 12 June 2026. Source check: 2484b9da-4c94-4042-9fac-61919b93e008
 * (capture-day POST /agent/full run).
 *
 * Abridgement policy — visible trims only, no field removal:
 * - Tru8: evidence array trimmed to representative items (every tier,
 *   a challenges relationship, archived URLs) with an in-place marker;
 *   everything else verbatim.
 * - Perplexity: results trimmed to 5 with an in-place marker.
 * - Google check-grounding and Parallel: shown whole, verbatim.
 * Raw unabridged captures: audit/2026-06-12_gap_analysis/captures/final/.
 *
 * Methodology (disclosed in the panel footers):
 * - Google check-grounding cannot take a claim alone: answerCandidate = the
 *   claim text; facts = the 17 sources Tru8's run retrieved.
 * - Parallel: Task API, processor "core" (a deeper tier than the cheapest,
 *   chosen deliberately), task spec quoted verbatim below. Wall-clock time is
 *   run creation -> completion.
 *
 * Regenerate: audit/2026-06-12_gap_analysis/captures/build_demo_data.py
 */

/** Capture date shown in the table footnote and every panel footer. */
export const CAPTURE_DATE = '12 June 2026';

/** The capture-day check behind the Tru8 panel, /r/ link and /verify link. */
export const CHECK_ID = '2484b9da-4c94-4042-9fac-61919b93e008';

/** The cast claim (Step 0a casting, user-approved). */
export const CLAIM_TEXT =
  'Moderate alcohol consumption protects against heart disease';

/** Parallel Task API spec, quoted verbatim in the panel footer. */
export const PARALLEL_TASK_SPEC =
  'Assess this claim and list supporting and opposing evidence with sources';

/** N sources Tru8's run retrieved, supplied to check-grounding as facts. */
export const GOOGLE_FACTS_COUNT = 17;

/** Wall-clock response time per live capture, shown in each panel header.
 *  Tru8 = pipeline processingTimeMs; Parallel = task create -> completed. */
export const CAPTURE_SECONDS = {
  tru8: '40.4s',
  perplexity: '1.0s',
  google: '2.8s',
  parallel: '4m 40s',
} as const;

/** Human-readable proof for /compare — the disputed element from the verified
 *  capture (mirrors the TRU8_RESPONSE element e3). Used by the on-page proof
 *  panel so a researcher can read the for-and-against without parsing JSON. */
export const TRU8_PROOF = {
  claim: CLAIM_TEXT,
  disputed: {
    description:
      'Individuals who consume alcohol moderately exhibit a lower incidence or severity of heart disease compared to those who do not consume alcohol or consume it heavily.',
    supports: 4,
    challenges: 6,
    context: 4,
    weightedSupports: 8,
    weightedChallenges: 15,
    uncertainty:
      'The scientific consensus on the cardiovascular benefits of moderate alcohol consumption is evolving, with newer research challenging previously accepted protective effects and suggesting potential risks even at low levels.',
    support:
      'An academic study found J- or U-shaped relationships between alcohol consumption and ischaemic heart disease, implying moderate consumption is associated with a lower risk than abstinence or heavy consumption for this condition.',
    challenge:
      'The American Heart Association states no research has proven a cause-and-effect link between drinking alcohol and better heart health, does not recommend drinking for health benefits, and notes moderation may worsen high blood pressure for some.',
  },
} as const;

export const TRU8_RESPONSE = `{
  "id": "2484b9da-4c94-4042-9fac-61919b93e008",
  "inputType": "text",
  "inputContent": {
    "input_type": "text",
    "content": "Moderate alcohol consumption protects against heart disease"
  },
  "inputUrl": null,
  "status": "completed",
  "creditsUsed": 0,
  "processingTimeMs": 40433,
  "errorMessage": null,
  "entryMode": "focused",
  "selectedClaimsCount": 1,
  "articleDomain": "Health",
  "articleSecondaryDomains": [],
  "articleJurisdiction": "Global",
  "articleClassificationSource": "llm_primary",
  "userQuery": null,
  "queryResponse": null,
  "queryConfidence": null,
  "querySources": null,
  "queryRelatedClaims": null,
  "claims": [
    {
      "id": "0df58c1b-1986-4801-8b78-28aa958f526e",
      "text": "Moderate alcohol consumption protects against heart disease",
      "position": 0,
      "claimMap": {
        "claimId": "0",
        "elements": [
          {
            "basis": {
              "evidence_count": 4,
              "tier_breakdown": {
                "primary": 2,
                "reporting": 2
              },
              "state_derivation": {
                "caveat": null,
                "rule_applied": "all_supports",
                "context_count": 1,
                "supports_count": 3,
                "challenges_count": 0,
                "weighted_supports": 8,
                "weighted_challenges": 0
              },
              "relationship_breakdown": {
                "context": 1,
                "supports": 3
              },
              "content_basis_breakdown": {
                "snippet": 1,
                "distilled": 3
              },
              "classification_breakdown": {
                "llm": 2,
                "llm+override": 2
              }
            },
            "state": "supported",
            "elementId": "e1",
            "description": "There is a defined level of alcohol consumption considered 'moderate'.",
            "uncertainty": null,
            "evidenceRefs": [
              {
                "reasoning": "The 2020–2025 Dietary Guidelines for Americans define moderate drinking as no more than two drinks per day for men and no more than one drink per day for women.",
                "evidenceId": "ev-b69dba1d2867",
                "relationship": "supports"
              },
              {
                "reasoning": "This academic study defines moderate intake as about one to two drinks per day, or 100g of alcohol per week, and also mentions <15.4 drinks/week for light to moderate consumption.",
                "evidenceId": "ev-afb1968e9454",
                "relationship": "supports"
              },
              {
                "reasoning": "The American Heart Association recommends limiting intake to ≤ two alcoholic drinks per day for men and one per day for women, and refers to 1-2 drinks/day as moderation.",
                "evidenceId": "ev-22c04ec329b7",
                "relationship": "supports"
              },
              {
                "reasoning": "This analysis discusses the cardiovascular risks associated with excessive alcohol use, which provides context for understanding the boundaries of moderate consumption.",
                "evidenceId": "ev-9e1e56f9d2be",
                "relationship": "context"
              }
            ]
          },
          {
            "basis": {
              "evidence_count": 4,
              "tier_breakdown": {
                "primary": 2,
                "reporting": 2
              },
              "state_derivation": {
                "caveat": null,
                "llm_state": "supported",
                "rule_applied": "all_supports",
                "context_count": 0,
                "supports_count": 4,
                "challenges_count": 0,
                "weighted_supports": 10,
                "weighted_challenges": 0
              },
              "relationship_breakdown": {
                "supports": 4
              },
              "content_basis_breakdown": {
                "snippet": 1,
                "distilled": 3
              },
              "classification_breakdown": {
                "llm": 2,
                "llm+override": 2
              }
            },
            "state": "supported",
            "elementId": "e2",
            "description": "Heart disease is a measurable condition.",
            "uncertainty": null,
            "evidenceRefs": [
              {
                "reasoning": "This analysis identifies specific heart conditions like atrial fibrillation, stroke, and heart failure, and mentions higher blood pressure, all of which are measurable.",
                "evidenceId": "ev-03fe6e7e29c5",
                "relationship": "supports"
              },
              {
                "reasoning": "This academic source discusses 'cardiovascular disease' and 'atrial fibrillation', indicating measurable conditions related to the heart.",
                "evidenceId": "ev-b69dba1d2867",
                "relationship": "supports"
              },
              {
                "reasoning": "This analysis lists measurable indicators of heart health such as blood pressure, heart rate, and risk of arrhythmia.",
                "evidenceId": "ev-cf29af2196cb",
                "relationship": "supports"
              },
              {
                "reasoning": "This academic study investigates 'carotid atherosclerosis' and uses measurable markers like CIMT, plaque score, and odds of stenosis.",
                "evidenceId": "ev-fc50b327c0a3",
                "relationship": "supports"
              }
            ]
          },
          {
            "basis": {
              "evidence_count": 14,
              "tier_breakdown": {
                "primary": 6,
                "reporting": 4,
                "commentary": 4
              },
              "state_derivation": {
                "caveat": "mixed: 4 support / 6 disagree (weighted 8 vs 15)",
                "rule_applied": "close_split",
                "context_count": 4,
                "supports_count": 4,
                "challenges_count": 6,
                "weighted_supports": 8,
                "weighted_challenges": 15
              },
              "relationship_breakdown": {
                "context": 4,
                "supports": 4,
                "challenges": 6
              },
              "content_basis_breakdown": {
                "snippet": 8,
                "distilled": 6
              },
              "classification_breakdown": {
                "llm": 8,
                "llm+override": 6
              }
            },
            "state": "disputed",
            "elementId": "e3",
            "description": "Individuals who consume alcohol moderately exhibit a lower incidence or severity of heart disease compared to those who do not consume alcohol or consume it heavily.",
            "uncertainty": "The scientific consensus on the cardiovascular benefits of moderate alcohol consumption is evolving, with newer research challenging previously accepted protective effects and suggesting potential risks even at low levels.",
            "evidenceRefs": [
              {
                "reasoning": "This academic study found the lowest mortality risk in patients with light to moderate alcohol consumption (8.4–15.4 drinks/week or <15.4 drinks/week) combined with physical activity, suggesting a protective association.",
                "evidenceId": "ev-afb1968e9454",
                "relationship": "supports"
              },
              {
                "reasoning": "This academic study found J- or U-shaped relationships between alcohol consumption and ischaemic heart disease, implying that moderate consumption is associated with a lower risk than abstinence or heavy consumption for this specific condition.",
                "evidenceId": "ev-8ad356eea484",
                "relationship": "supports"
              },
              {
                "reasoning": "This commentary states that moderate alcohol consumption was associated with a 22% reduction in cardiovascular death, supporting a protective effect.",
                "evidenceId": "ev-a70c8119a54e",
                "relationship": "supports"
              },
              {
                "reasoning": "This commentary notes that epidemiological studies suggest moderate consumption of beer or wine may confer greater cardiovascular protection.",
                "evidenceId": "ev-3aeaab5aacac",
                "relationship": "supports"
              },
              {
                "reasoning": "Newer, better-quality research suggests alcohol offers little to no real protection for the heart and is linked to higher blood pressure and increased risk of conditions like atrial fibrillation, stroke, and heart failure, even at low levels.",
                "evidenceId": "ev-03fe6e7e29c5",
                "relationship": "challenges"
              },
              {
                "reasoning": "This academic source states that the cardiovascular effects of light to moderate drinking remain uncertain and that it's not possible to answer whether it can lower risk with current evidence, also noting potential worry for atrial fibrillation.",
                "evidenceId": "ev-b69dba1d2867",
                "relationship": "challenges"
              },
              {
                "reasoning": "Recent studies using new methodologies have challenged the idea of positive health effects from any level of alcohol consumption, suggesting little or no protection rather than harm.",
                "evidenceId": "ev-21c3e5cca608",
                "relationship": "challenges"
              },
              {
                "reasoning": "The American Heart Association states no research has proven a direct cause-and-effect link between drinking alcohol and better heart health, does not recommend drinking for health benefits, and notes moderation may worsen high blood pressure for some.",
                "evidenceId": "ev-22c04ec329b7",
                "relationship": "challenges"
              },
              {
                "reasoning": "The WHO states there is no evidence to show a safe level of drinking and no studies have shown potential heart health benefits.",
                "evidenceId": "ev-d1a67bb83f36",
                "relationship": "challenges"
              },
              {
                "reasoning": "Genetic epidemiology suggests that alcohol consumption of all amounts is associated with increased cardiovascular risk.",
                "evidenceId": "ev-28acf4c49073",
                "relationship": "challenges"
              },
              {
                "reasoning": "This academic source notes that for decades, studies suggested moderate alcohol intake could protect the heart, providing historical context for the claim.",
                "evidenceId": "ev-ac6b32f9a6ef",
                "relationship": "context"
              },
              {
                "reasoning": "This news report highlights the ongoing and perennial debate regarding whether light to moderate drinking provides cardiovascular protection.",
                "evidenceId": "ev-abb854aa867b",
                "relationship": "context"
              },
              {
                "reasoning": "This commentary discusses how heavy episodic drinking can negate protective associations, thereby providing context for the definition and impact of moderate alcohol consumption on heart disease.",
                "evidenceId": "ev-903468afbec0",
                "relationship": "context"
              },
              {
                "reasoning": "This academic guideline mentions reducing or eliminating alcohol intake as part of cardiovascular risk management, which contextualizes the claim about moderate alcohol consumption and heart disease.",
                "evidenceId": "ev-5ef96a6a9f90",
                "relationship": "context"
              }
            ]
          }
        ],
        "metadata": {
          "completedAt": "2026-06-12T16:18:12.177705+00:00",
          "elementCount": 3,
          "mappingModel": "gemini-2.5-flash-lite",
          "decompositionModel": "gemini-2.5-flash-lite"
        },
        "claimType": "empirical",
        "orientation": "Of 3 elements examined, 2 predominantly supported; 1 with conflicting evidence.",
        "normalisedClaim": "Moderate alcohol consumption is associated with a reduced risk of heart disease.",
        "orientationBasis": {
          "total_elements": 3,
          "state_distribution": {
            "disputed": 1,
            "supported": 2,
            "contextual": 0,
            "unresolved": 0
          }
        }
      },
      "claimType": "empirical",
      "isSelected": true,
      "significanceRank": 1,
      "subjectContext": "Alcohol and heart disease",
      "keyEntities": [
        {
          "text": "Moderate alcohol consumption",
          "type": "OTHER"
        },
        {
          "text": "heart disease",
          "type": "OTHER"
        }
      ],
      "sourceTitle": null,
      "sourceUrl": null,
      "sourcesReviewedCount": 3,
      "evidence": [
        {
          "id": "a5a4f4c8-e826-4882-ac53-69072629f8c5",
          "evidenceId": "ev-d1a67bb83f36",
          "source": "victorchang.edu.au",
          "url": "https://www.victorchang.edu.au/blog/alcohol-and-the-heart",
          "title": "Alcohol & Heart Health | Victor Chang Cardiac Research Institute",
          "snippet": "WHO agreed that there is currently no evidence to show a safe level of drinking, and that no studies have shown that the potential heart health benefits of ...",
          "publishedDate": "2025-07-21T00:00:00",
          "relevanceScore": 0.5,
          "tier": "primary",
          "evidenceType": "academic",
          "receiptStatus": "shown",
          "corroborationGroupId": 1,
          "corroboratingEvidenceIds": "ev-abb854aa867b,ev-903468afbec0",
          "isFactcheck": false,
          "externalSourceProvider": null,
          "sourceType": null,
          "archivedUrl": "https://web.archive.org/web/20260612145549/https://www.victorchang.edu.au/blog/alcohol-and-the-heart",
          "llmRelevanceScore": 4,
          "classificationMethod": "llm+override",
          "contentBasis": "snippet"
        },
        {
          "id": "87774bfc-5198-4816-a32f-f2661d9d9c29",
          "evidenceId": "ev-8ad356eea484",
          "source": "nature.com",
          "url": "https://www.nature.com/articles/s44360-026-00139-5",
          "title": "Health effects associated with alcohol consumption: a Burden of ...",
          "snippet": "- The relationship between alcohol and health is complex, and the evidence relating alcohol consumption to various cardiovascular diseases, cancers and other conditions is evolving.\\n- We found that levels of current alcohol consumption are associated with increased risks for cancers of the breast, colorectum, oesophagus, larynx, lip and oral cavities, pharynx, liver, stomach, pancreas and prostate, as well as pancreatitis, cirrhosis and other chronic liver diseases, lower respiratory infections, tuberculosis, and atrial fibrillation and flutter.\\n- We found J- or U-shaped relationships between alcohol consumption and type 2 diabetes, Alzheimer’s disease and other dementias, ischaemic heart disease, ischaemic stroke and haemorrhagic stroke.\\n- While potential health impacts at low-to-moderate levels varied by outcome, high levels of alcohol consumption were associated with increased risk across all outcomes.\\n- Meta-analyses of observational studies have consistently demonstrated that even low levels of alcohol intake are associated with increased risks of several cancers and liver disease, with escalating risk as intake increases.\\n- Conversely, low-to-moderate consumption (generally up to two standard drinks or 20 g of pure alcohol per day) has been associated with reduced risk of cardiovascular disease, type 2 diabetes and dementia.\\n- However, these associations attenuate or reverse at higher intake.\\n- The Burden of Proof approach uses a six-step meta-analytic framework to objectively and comparatively quantify the strength of evidence linking risk factors to health outcomes.",
          "publishedDate": "2026-06-01T00:00:00",
          "relevanceScore": 0.6388888888888888,
          "tier": "primary",
          "evidenceType": "academic",
          "receiptStatus": "shown",
          "corroborationGroupId": null,
          "corroboratingEvidenceIds": null,
          "isFactcheck": false,
          "externalSourceProvider": null,
          "sourceType": null,
          "archivedUrl": "https://web.archive.org/web/20260612145817/https://www.nature.com/articles/s44360-026-00139-5",
          "llmRelevanceScore": 4,
          "classificationMethod": "llm+override",
          "contentBasis": "distilled"
        },
        {
          "id": "3f2b0a76-8d1b-49e3-8674-8651bbecd13c",
          "evidenceId": "ev-03fe6e7e29c5",
          "source": "heartfoundation.org.au",
          "url": "https://www.heartfoundation.org.au/healthy-living/healthy-eating/alcohol-and-heart-health",
          "title": "Alcohol and Heart Health - Heart Foundation",
          "snippet": "- In the past, some studies suggested that drinking small amounts of alcohol might be good for your heart, while heavy drinking was clearly harmful.\\n- But newer, better-quality research shows that the supposed benefits of light drinking may not be due to alcohol itself.\\n- Instead, they might be because light drinkers often have healthier lifestyles overall.\\n- Recent studies now suggest that alcohol offers little to no real protection for your heart.\\n- Research shows that alcohol is linked to higher blood pressure and an increased risk of conditions like atrial fibrillation, stroke and heart failure.\\n- High-quality studies, including those looking at just one standard drink, have found that even low levels of alcohol can raise the risk of heart disease.\\n- Moderate drinking can also raise blood pressure, especially in people who already have high blood pressure, and may make existing heart problems like atrial fibrillation worse.\\n- There is now strong evidence that drinking alcohol doesn’t have any heart health benefits and isn’t recommended as part of a heart-healthy eating pattern.",
          "publishedDate": "2026-01-04T00:00:00",
          "relevanceScore": 0.0410958904109589,
          "tier": "reporting",
          "evidenceType": "analysis",
          "receiptStatus": "shown",
          "corroborationGroupId": null,
          "corroboratingEvidenceIds": null,
          "isFactcheck": false,
          "externalSourceProvider": null,
          "sourceType": null,
          "archivedUrl": "https://web.archive.org/web/20260612144522/https://www.heartfoundation.org.au/healthy-living/healthy-eating/alcohol-and-heart-health",
          "llmRelevanceScore": 3,
          "classificationMethod": "llm",
          "contentBasis": "distilled"
        },
        {
          "id": "c5bbc4bc-aa29-401d-ab90-c1321655ddc4",
          "evidenceId": "ev-21c3e5cca608",
          "source": "medscape.com",
          "url": "https://www.medscape.com/viewarticle/new-aha-scientific-statement-reconsiders-moderate-alcohol-2025a1000g00",
          "title": "AHA: Effects of Modest Alcohol Use on the Heart Unclear - Medscape",
          "snippet": "- Several medical groups have concluded regular consumption of alcohol in any amount poses a health risk, but a new scientific statement from the American Heart Association (AHA) offered more qualified guidance.\\n- The premise that moderate alcohol use reduces cardiovascular risk has been widely accepted for decades.\\n- However, a review of the evidence in 2025 produced a more cautious summary.\\n- Data from recent studies using new methodologies (eg, individual participant-level data meta-analysis and Mendelian randomization [MR]) have challenged the idea that any level of alcohol consumption has positive health effects.\\n- Prior to the new methodologies, protection against coronary artery disease from moderate alcohol use was derived from many observational studies.\\n- The new methodologies for addressing the question of the safety of moderate drinking do not fully reverse conclusions that it is beneficial.\\n- They suggest little or no protection rather than harm.\\n- For coronary artery disease specifically, the AHA statement acknowledged that moderate drinking “may provide some risk reduction” for the condition even if this reduction has been rendered less clear by studies using analyses designed to apply more rigor for evaluating observational data.",
          "publishedDate": "2025-06-16T00:00:00",
          "relevanceScore": 0.15970149253731344,
          "tier": "reporting",
          "evidenceType": "news_reporting",
          "receiptStatus": "shown",
          "corroborationGroupId": 2,
          "corroboratingEvidenceIds": "ev-22c04ec329b7",
          "isFactcheck": false,
          "externalSourceProvider": null,
          "sourceType": null,
          "archivedUrl": "https://web.archive.org/web/20260612144843/https://www.medscape.com/viewarticle/new-aha-scientific-statement-reconsiders-moderate-alcohol-2025a1000g00",
          "llmRelevanceScore": 5,
          "classificationMethod": "llm",
          "contentBasis": "distilled"
        },
        {
          "id": "760b8fe7-f83e-4252-9bb0-bf63f598c8cb",
          "evidenceId": "ev-a70c8119a54e",
          "source": "dx.doi.org",
          "url": "https://dx.doi.org/10.15288/jsad.25-00075",
          "title": "The U.S. National Academies of Science, Engineering, and ...",
          "snippet": "They concluded that moderate alcohol consumption was associated with a 16% reduction in death from all causes (n = 8 studies), a 22% reduction in cardiovascular ...",
          "publishedDate": "2025-06-30T00:00:00",
          "relevanceScore": 0.5,
          "tier": "commentary",
          "evidenceType": "academic",
          "receiptStatus": "shown",
          "corroborationGroupId": 1,
          "corroboratingEvidenceIds": "ev-ac6b32f9a6ef,ev-abb854aa867b,ev-28acf4c49073,ev-3aeaab5aacac",
          "isFactcheck": false,
          "externalSourceProvider": null,
          "sourceType": null,
          "archivedUrl": null,
          "llmRelevanceScore": 4,
          "classificationMethod": "llm",
          "contentBasis": "snippet"
        },
        // … 12 more evidence items — full response: /r/2484b9da-4c94-4042-9fac-61919b93e008
      ]
    }
  ],
  "createdAt": "2026-06-12T16:17:30.848797",
  "completedAt": "2026-06-12T16:18:12.190642",
  "currentStage": null,
  "progress": null,
  "progressMessage": null,
  "_meta": {
    "executedTier": "full",
    "chargedPence": 0,
    "limitations": [],
    "landscape": {
      "elementCount": 3,
      "elementStates": {
        "supported": 2,
        "disputed": 1
      },
      "evidenceDensity": 17,
      "sourcesConsidered": 17,
      "sourceDiversity": {
        "tierSpread": {
          "reporting": 6,
          "primary": 7,
          "commentary": 4
        },
        "uniqueDomains": 14,
        "typeCoverage": 4
      },
      "freshness": {
        "freshestDaysAgo": 11,
        "dateSpanDays": 350,
        "undatedCount": 1
      },
      "gaps": [],
      "providerStatus": null
    }
  },
  "_computed": {
    "summary": {
      "totalClaims": 1,
      "totalEvidence": 17,
      "totalElements": 3,
      "elementStates": {
        "supported": 2,
        "disputed": 1,
        "unresolved": 0
      },
      "coveragePercent": 100.0,
      "gapElements": []
    },
    "evidenceByTier": {
      "reporting": 6,
      "primary": 7,
      "commentary": 4
    },
    "evidenceByType": {
      "analysis": 3,
      "news_reporting": 2,
      "academic": 11,
      "official_statement": 1
    },
    "heatmap": [
      {
        "tier": "commentary",
        "type": "academic",
        "count": 4
      },
      {
        "tier": "primary",
        "type": "academic",
        "count": 7
      },
      {
        "tier": "reporting",
        "type": "analysis",
        "count": 3
      },
      {
        "tier": "reporting",
        "type": "news_reporting",
        "count": 2
      },
      {
        "tier": "reporting",
        "type": "official_statement",
        "count": 1
      }
    ],
    "corroboration": {
      "groups": [
        {
          "groupId": 2,
          "evidenceIds": [
            "ev-21c3e5cca608",
            "ev-22c04ec329b7",
            "ev-b69dba1d2867"
          ],
          "tiers": [
            "primary",
            "reporting"
          ],
          "size": 3
        },
        {
          "groupId": 1,
          "evidenceIds": [
            "ev-abb854aa867b",
            "ev-d1a67bb83f36",
            "ev-a70c8119a54e",
            "ev-903468afbec0",
            "ev-5ef96a6a9f90",
            "ev-3aeaab5aacac",
            "ev-ac6b32f9a6ef",
            "ev-9e1e56f9d2be",
            "ev-28acf4c49073"
          ],
          "tiers": [
            "commentary",
            "primary",
            "reporting"
          ],
          "size": 9
        },
        {
          "groupId": 3,
          "evidenceIds": [
            "ev-cf29af2196cb",
            "ev-fc50b327c0a3"
          ],
          "tiers": [
            "primary",
            "reporting"
          ],
          "size": 2
        }
      ],
      "convergenceCount": 2
    },
    "diagnosticValues": {
      "hasDiagnosticVariance": true,
      "highCount": 3,
      "totalCount": 17,
      "values": {
        "ev-b69dba1d2867": 1.0,
        "ev-afb1968e9454": 0.6,
        "ev-22c04ec329b7": 1.0,
        "ev-9e1e56f9d2be": 0.1,
        "ev-03fe6e7e29c5": 1.0,
        "ev-cf29af2196cb": 0.6,
        "ev-fc50b327c0a3": 0.6,
        "ev-8ad356eea484": 0.6,
        "ev-a70c8119a54e": 0.6,
        "ev-3aeaab5aacac": 0.6,
        "ev-21c3e5cca608": 0.6,
        "ev-d1a67bb83f36": 0.6,
        "ev-28acf4c49073": 0.6,
        "ev-ac6b32f9a6ef": 0.1,
        "ev-abb854aa867b": 0.1,
        "ev-903468afbec0": 0.1,
        "ev-5ef96a6a9f90": 0.1
      }
    },
    "timeline": {
      "datedCount": 16,
      "undatedCount": 1,
      "dateRange": {
        "earliest": "2025-06-16T00:00:00",
        "latest": "2026-06-01T00:00:00"
      },
      "belowThreshold": false,
      "gaps": [
        {
          "afterDate": "2025-10-01T00:00:00",
          "beforeDate": "2025-11-19T00:00:00",
          "gapDays": 49
        },
        {
          "afterDate": "2026-01-04T00:00:00",
          "beforeDate": "2026-03-04T00:00:00",
          "gapDays": 59
        },
        {
          "afterDate": "2026-03-04T00:00:00",
          "beforeDate": "2026-06-01T00:00:00",
          "gapDays": 89
        }
      ]
    },
    "freshness": {
      "freshestDaysAgo": 11,
      "dateSpanDays": 350,
      "undatedCount": 1
    },
    "uniqueDomains": 14,
    "perClaim": [
      {
        "claimPosition": 0,
        "elementCount": 3,
        "evidenceCount": 17,
        "elementStates": {
          "supported": 2,
          "disputed": 1,
          "unresolved": 0
        },
        "coveragePercent": 100.0,
        "evidenceByTier": {
          "reporting": 6,
          "primary": 7,
          "commentary": 4
        },
        "dispositions": {
          "e1": {
            "supports": [
              "ev-b69dba1d2867",
              "ev-afb1968e9454",
              "ev-22c04ec329b7"
            ],
            "challenges": [],
            "context": [
              "ev-9e1e56f9d2be"
            ]
          },
          "e2": {
            "supports": [
              "ev-03fe6e7e29c5",
              "ev-b69dba1d2867",
              "ev-cf29af2196cb",
              "ev-fc50b327c0a3"
            ],
            "challenges": [],
            "context": []
          },
          "e3": {
            "supports": [
              "ev-afb1968e9454",
              "ev-8ad356eea484",
              "ev-a70c8119a54e",
              "ev-3aeaab5aacac"
            ],
            "challenges": [
              "ev-03fe6e7e29c5",
              "ev-b69dba1d2867",
              "ev-21c3e5cca608",
              "ev-22c04ec329b7",
              "ev-d1a67bb83f36",
              "ev-28acf4c49073"
            ],
            "context": [
              "ev-ac6b32f9a6ef",
              "ev-abb854aa867b",
              "ev-903468afbec0",
              "ev-5ef96a6a9f90"
            ]
          }
        }
      }
    ]
  },
  "_manifest": {
    "checkId": "2484b9da-4c94-4042-9fac-61919b93e008",
    "landscapeHash": "645ad4af0ecda883bdd3c6851a5f8e80eb1691468ac8b45f876eedc87ed11084",
    "signedAt": "2026-06-12T16:18:12.237251+00:00",
    "signature": "hmac-sha256:adfc331f31174e0e427815d65a3ba620791da314a56d6f03d80ee792886c79eb",
    "kid": "tru8-2026-03",
    "verifyUrl": "/verify/2484b9da-4c94-4042-9fac-61919b93e008"
  }
}`;

export const PERPLEXITY_RESPONSE = `{
  "id": "5dd67ba2-6a0d-4a62-82e3-408ea550d5fb",
  "results": [
    {
      "last_updated": "2025-08-14",
      "snippet": "Some studies have shown an association between moderate alcohol intake and a lower risk of dying from heart disease.\\nBut it’s hard to determine cause and effect from those studies.\\nPerhaps people who sip red wine have higher incomes, which tend to be associated with more education and greater access to healthier foods.\\nSimilarly, red wine drinkers might be more likely to eat a heart-healthy diet.\\nThere is some evidence that moderate amounts of alcohol might help to slightly raise levels of “good” HDL cholesterol.\\nResearchers have also suggested that red wine, in particular, might protect the heart, thanks to the antioxidants it contains.\\nBut you don’t have to pop a cork to reap those benefits.\\nExercise can also boost HDL cholesterol levels, and antioxidants can be found in other foods, such as fruits, vegetables and grape juice.\\n...\\nWhether or not moderate drinking is good for your heart is open to debate.\\nHowever, for most people, it doesn’t appear to be harmful to the heart — but the key word is “moderate.”\\nModerate drinking is defined as an average of one drink per day for women and one or two for men.\\nA drink might be less than you think: 12 ounces of beer, 4 ounces of wine or 1.5 ounces of 80-proof spirits.\\nSome people should avoid even that much and not drink at all if they have certain heart rhythm abnormalities or have heart failure.\\n...\\nHeavy drinking, on the other hand, is linked to a number of poor health outcomes, including heart conditions.\\nExcessive alcohol intake can lead to high blood pressure, heart failure or stroke.\\nExcessive drinking can also contribute to cardiomyopathy, a disorder that affects the heart muscle.\\n...\\nThe takeaway is what you probably already knew: If you choose to drink alcohol, stick to moderate levels of drinking, and don’t overdo it.",
      "title": "Alcohol and Heart Health: Separating Fact from Fiction",
      "url": "https://www.hopkinsmedicine.org/health/wellness-and-prevention/alcohol-and-heart-health-separating-fact-from-fiction"
    },
    {
      "date": "2025-06-09",
      "last_updated": "2025-08-13",
      "snippet": "",
      "title": "Alcohol Use and Cardiovascular Disease: A Scientific Statement ...",
      "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341"
    },
    {
      "date": "2024-01-01",
      "last_updated": "2026-06-05",
      "snippet": "Drinking excessive amounts of alcoholic beverages damages many organs, particularly the liver, brain, and heart.\\nParadoxically, however, beginning about 50 years ago, studies began to suggest that moderate drinking might actually be good for the heart.\\nModerate drinking is defined as one to two drinks per day for a man, and one drink per day for a woman.\\nA \\"drink\\" is defined as a shot (1.5 ounces) of spirits, a 5-ounce glass of wine, or a 12-ounce bottle of beer.\\n...\\nThe evidence for a heart benefit from moderate drinking comes from observational research involving hundreds of thousands of people whose drinking patterns and health have been closely followed for decades.\\nPeople in these investigations have been divided into roughly three groups: nondrinkers, moderate drinkers, and more-than-moderate drinkers.\\nOver time, moderate drinkers have had lower rates of coronary artery disease (including fewer heart attacks) compared to both of the other two groups.\\n\\"That makes sense, since other studies have found that moderate drinking causes 'good' cholesterol to rise and blood to clot a bit less easily - both of which could explain a lower rate of heart attacks,\\" says Dr. Anthony Komaroff, an internal medicine specialist and *Health Letter * editor in chief.\\nBased on these results, the current Dietary Guidelines for Americans recommend drinking only in moderation, if at all.\\nOther authoritative organizations - such as the CDC and the American Heart Association - have echoed this advice.\\nHowever, none of these guidelines recommend moderate drinking as a way of protecting against heart disease, because observational studies cannot prove the value of a drug or a practice, such as moderate drinking.\\n...\\nIf an observational study finds that people who have just one drink a day are less likely to develop heart disease than people who do not drink, that does not necessarily mean that the moderate drinking pattern is the reason for the lower rate of heart disease.\\n...\\nIn considering whether moderate drinking improves heart health, we are left with large observational studies.\\nSeveral recent investigations have not found clear evidence that people who take a drink a day are less likely to develop heart disease than people who don't drink.\\nThis new evidence doesn't negate past studies; it simply must be weighed against past studies.\\n## Our best current assessment\\nAs of now, the evidence leads us to these conclusions:\\n- Moderate drinking may offer some heart benefits, but we don't recommend it for the purpose of achieving those unproven benefits.\\n- Alcohol avoidance is not harmful, although there is some evidence that moderate drinkers who then stop may subsequently have a somewhat higher risk of developing diabetes and heart disease.\\n- Excessive drinking - averaging three or more drinks a day - causes multiple health problems, including heart problems.",
      "title": "Is moderate drinking heart-healthy? - Harvard Health",
      "url": "https://www.health.harvard.edu/heart-health/is-moderate-drinking-heart-healthy"
    },
    {
      "date": "2022-03-25",
      "last_updated": "2026-06-10",
      "snippet": "> Reducing alcohol intake will likely reduce cardiovascular risk in all individuals.\\n**BOSTON –** Observational research has suggested that light alcohol consumption may provide heart-related health benefits, but in a large study published in *JAMA Network Open*, alcohol intake at all levels was linked with higher risks of cardiovascular disease.\\nThe findings, which are published by a team led by researchers at Massachusetts General Hospital (MGH) and the Broad Institute of MIT and Harvard, suggest that the supposed benefits of alcohol consumption may actually be attributed to other lifestyle factors that are common among light to moderate drinkers.\\n...\\nConsistent with earlier studies, investigators found that light to moderate drinkers had the lowest heart disease risk, followed by people who abstained from drinking.\\nPeople who drank heavily had the highest risk.\\nHowever, the team also found that light to moderate drinkers tended to have healthier lifestyles than abstainers—such as more physical activity and vegetable intake, and less smoking.\\nTaking just a few lifestyle factors into account significantly lowered any benefit associated with alcohol consumption.\\n...\\nWhen the scientists conducted such genetic analyses of samples taken from participants, they found that individuals with genetic variants that predicted higher alcohol consumption were indeed more likely to consume greater amounts of alcohol, and more likely to have hypertension and coronary artery disease.\\nThe analyses also revealed substantial differences in cardiovascular risk across the spectrum of alcohol consumption among both men and women, with minimal increases in risk when going from zero to seven drinks per week, much higher risk increases when progressing from seven to 14 drinks per week, and especially high risk when consuming 21 or more drinks per week.\\nNotably, the findings suggest a rise in cardiovascular risk even at levels deemed “low risk” by national guidelines from the U.S. Department of Agriculture (i.e. below two drinks per day for men and one drink per day for women).\\nThe discovery that the relationship between alcohol intake and cardiovascular risk is not a linear one but rather an exponential one was supported by an additional analysis of data on 30,716 participants in the Mass General Brigham Biobank.\\nTherefore, while cutting back on consumption can benefit even people who drink one alcoholic beverage per day, the health gains of cutting back may be more substantial – and, perhaps, more clinically meaningful – in those who consume more.\\n“The findings affirm that alcohol intake should not be recommended to improve cardiovascular health; rather, that reducing alcohol intake will likely reduce cardiovascular risk in all individuals, albeit to different extents based on one’s current level of consumption,” says Aragam.",
      "title": "Large study challenges the theory that light alcohol consumption ...",
      "url": "https://www.massgeneral.org/news/press-release/Large-study-challenges-the-theory-that-light-alcohol-consumption-benefits-heart-health"
    },
    {
      "date": "2025-09-30",
      "last_updated": "2026-06-05",
      "snippet": "Recommendation: If you don’t drink alcohol, don’t start.\\nIf you choose to drink alcohol, limit your intake.\\n...\\nDrinking alcohol in moderation means no more than one to two drinks per day for men and no more than one drink per day for women.\\n...\\nBoth binge drinking (five or more drinks in a day for men or four or more drinks for women if consumed within approximately 2 hours) and heavy drinking (four or more drinks per day, or engaging in binge drinking 5 or more days within the past 30 days) increase risk for every cardiovascular condition, including high blood pressure, stroke, irregular heart rhythm, heart failure and sudden cardiac death.\\nAnd even moderate drinking may increase blood pressure in some individuals.\\n...\\nThere have been plenty of headlines about studies associating light or moderate drinking with health benefits and reduced mortality.\\nSome researchers have suggested that wine has health benefits, especially red wine, and that a glass a day can be good for the heart.\\nNo research has proven a cause-and-effect link between drinking alcohol and better heart health.\\nComponents in red wine, such as flavonoids and other antioxidants, can potentially reduce heart disease risk, but they also can be found in other foods, such as grapes, red grape juice or blueberries.\\nIt’s unclear whether red wine is directly associated with the health benefits seen in some studies or whether other factors are at play.\\nModerate wine drinkers might be more likely to have a healthier diet and lifestyle — including eating lots of fruits and vegetables and being physically active.\\nThe American Heart Association does not recommend drinking wine or any other form of alcohol to gain potential health benefits.\\nInstead, take Life’s Essential 8 steps to improve cardiovascular health: eat a healthy diet, be active, get healthy sleep, quit tobacco, and manage weight, blood cholesterol, blood sugar, and blood pressure.\\n...\\nWhile some research suggests no effect or even reduced risk for heart disease and stroke from moderate drinking, all the evidence together does not support benefits for the general population.\\nIn fact, for some people, even one to two drinks per day can increase blood pressure.\\nPeople should consult with their health care professionals regarding the consumption and possible risks and benefits of alcohol.\\nThe American Heart Association does not advise anyone to drink for reasons of benefiting their health.\\nAnd if someone chooses to drink, it should be done in moderation for overall well-being.\\n...\\nDrink alcoholic beverages only in moderation, if at all.\\nIf you do drink, be sure to understand the potential effects on your health.\\nAnd don’t start drinking for health benefits; these are unproven.",
      "title": "Is drinking alcohol part of a healthy lifestyle?",
      "url": "https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/alcohol-and-heart-health"
    },
    // … 5 more results
  ]
}`;

export const GOOGLE_RESPONSE = `{
  "supportScore": 0.8599525,
  "citedChunks": [
    {
      "chunkText": "Epidemiological studies suggest that moderate consumption of either beer or wine may confer greater cardiovascular protection than spirits.",
      "source": "15"
    },
    {
      "chunkText": "For decades, studies suggested that moderate alcohol intake could protect the heart, reduce diabetes risk, or even help you live longer.",
      "source": "16"
    }
  ],
  "claims": [
    {
      "startPos": 0,
      "endPos": 59,
      "claimText": "Moderate alcohol consumption protects against heart disease",
      "citationIndices": [
        0,
        1
      ],
      "groundingCheckRequired": true
    }
  ]
}`;

export const PARALLEL_RESPONSE = `{
  "run": {
    "run_id": "trun_b39d08eb16914bb6a83724884fe01f6f",
    "interaction_id": "trun_b39d08eb16914bb6a83724884fe01f6f",
    "status": "completed",
    "is_active": false,
    "processor": "core",
    "metadata": {},
    "created_at": "2026-06-12T15:32:44.838051Z",
    "modified_at": "2026-06-12T15:37:24.517143Z"
  },
  "output": {
    "basis": [
      {
        "field": "output",
        "citations": [
          {
            "title": "Association of alcohol consumption with selected ...",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3043109/",
            "excerpts": []
          },
          {
            "title": "Moderate alcohol intake and lower risk of coronary heart ...",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC28294/",
            "excerpts": []
          },
          {
            "title": "Association between alcohol and cardiovascular disease ...",
            "url": "https://www.bmj.com/content/349/bmj.g4164",
            "excerpts": []
          },
          {
            "title": "Alcohol use and burden for 195 countries and territories ...",
            "url": "https://www.thelancet.com/pdfs/journals/lancet/PIIS0140-6736(18)31310-2.pdf",
            "excerpts": [
              "the risk of all-cause mortality, and of cancers specifically, rises with increasing levels of consumption, and the level of consumption that minimises health loss is zero."
            ]
          },
          {
            "title": "Alcohol Use and Cardiovascular Disease: A Scientific Statement ...",
            "url": "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341",
            "excerpts": []
          }
        ],
        "reasoning": "The analysis was conducted by synthesizing data from observational meta-analyses and experimental biomarker studies which support a protective association, and contrasting them with Mendelian randomization and population-level health burden studies which suggest no benefit or potential harm. The final assessment reflects a balanced view, acknowledging the observed associations while highlighting the lack of causal evidence and the recommendations of major health organizations.",
        "confidence": "medium"
      }
    ],
    "type": "text",
    "content": "Claim: Moderate alcohol consumption protects against heart disease.\\n\\nShort Answer: Observational and short-term experimental evidence show that light-to-moderate drinking is associated with lower rates of coronary heart disease and favorable changes in some cardiovascular biomarkers. However, more robust causal-evidence methods like Mendelian randomization, large-scale burden analyses, and concerns about bias (especially the 'sick-quitter' effect and residual confounding) challenge the idea that initiating alcohol use for cardioprotection is beneficial. Major cardiovascular organizations do not recommend starting drinking to prevent heart disease. Overall, the balance of evidence is uncertain for a causal protective effect; the safest public-health message is not to start drinking for heart protection, and to minimize alcohol for other health reasons.\\n\\nSupporting Evidence (Observational / Mechanistic):\\n- Large observational meta-analyses and cohort studies report J-shaped associations: light-to-moderate drinkers have lower coronary heart disease (CHD) incidence and CHD mortality than abstainers. For example, a systematic review and meta-analysis pooling cohort studies found pooled adjusted relative risks for incident CHD of approximately 0.71 for drinkers versus non-drinkers.\\n- Short-term randomized intervention studies show that moderate alcohol increases HDL cholesterol and changes haemostatic factors (e.g., fibrinogen) in directions predicted to reduce CHD risk.\\n\\nOpposing Evidence (Causal Inference / Public Health / Bias):\\n- Mendelian randomization (MR) analyses using genetic proxies for lower alcohol consumption indicate that genetically lower alcohol intake is associated with lower blood pressure, lower inflammatory biomarkers, and a reduced risk of coronary heart disease. This suggests that reductions of alcohol consumption, even for light-to-moderate drinkers, may be beneficial for cardiovascular health.\\n- Global Burden of Disease and Lancet analyses concluded that when all alcohol-related harms (including cancer, injury, and other diseases) are considered, the level of consumption that minimizes health loss is zero.\\n- Observational designs are prone to significant biases, including confounding by socioeconomic and lifestyle factors, reverse causation (the 'sick-quitter' effect where former drinkers who stopped due to illness are grouped with lifelong abstainers), and measurement error in self-reported drinking.\\n- There are no large randomized controlled trials with clinical cardiovascular endpoints showing a benefit of initiating moderate alcohol consumption."
  }
}`;

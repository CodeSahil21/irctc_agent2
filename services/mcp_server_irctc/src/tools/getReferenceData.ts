/**
 * Merged tool: replaces list_classes + list_quotas.
 * Returns both static reference tables in one call.
 */
export function getReferenceDataTool(): {
  classes: { code: string; name: string }[];
  quotas: { code: string; name: string }[];
} {
  return {
    classes: [
      { code: "SL",  name: "Sleeper" },
      { code: "3A",  name: "AC 3 Tier" },
      { code: "2A",  name: "AC 2 Tier" },
      { code: "1A",  name: "AC First Class" },
      { code: "CC",  name: "AC Chair Car" },
      { code: "EC",  name: "Executive Chair Car" },
      { code: "2S",  name: "Second Sitting" },
      { code: "VS",  name: "Vistadome AC" },
    ],
    quotas: [
      { code: "GN", name: "General" },
      { code: "LD", name: "Ladies" },
      { code: "TQ", name: "Tatkal" },
      { code: "PT", name: "Premium Tatkal" },
      { code: "HO", name: "Higher Official" },
      { code: "SS", name: "Senior Citizen" },
    ],
  };
}

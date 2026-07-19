export function listQuotasTool(): { code: string; name: string }[] {
  return [
    { code: "GN", name: "General" },
    { code: "LD", name: "Ladies" },
    { code: "TQ", name: "Tatkal" },
    { code: "PT", name: "Premium Tatkal" },
    { code: "HO", name: "Higher Official" },
    { code: "SS", name: "Senior Citizen" },
  ];
}

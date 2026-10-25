def checklist(status: str, has_rera: bool) -> list[str]:
    base = [
        "Title search for 30 years via a property lawyer; confirm chain of ownership on Index-II (IGR).",
        "Pull registered Index-II records for the same building to confirm the deal price you were quoted.",
        "Confirm the seller's ownership documents, society share certificate and NOC for sale.",
        "Check property-tax and society dues are cleared; ask for a no-dues certificate.",
        "Visit at day and night: water, noise, parking, building condition, structural audit status.",
        "Check mortgage lien: if the seller has a loan, get the bank's NOC/original documents plan.",
        "Agreement for sale: stamp duty on the registered value; TDS 1% via Form 26QB if > ₹50 lakh.",
    ]
    if status == "under_construction":
        base += [
            "Verify project, promoter and RERA number on maharerait.maharashtra.gov.in; read the latest QPR.",
            "Check Commencement Certificate, approved plans and encumbrance; confirm 70% RERA escrow rule applies.",
            "Payment plan should be linked to construction milestones; max 10% before registered agreement.",
            "Agreement must carry carpet area (RERA); do not accept 'saleable' as the pricing basis.",
        ]
    else:
        base += [
            "Occupation Certificate (OC) and Completion Certificate must exist; no OC means no home loan and legal risk.",
            "Redevelopment status/plans of the society: they affect both value and your timeline.",
        ]
    if not has_rera:
        base.append("No RERA number provided: ask for it, or confirm the building is exempt (completed before 2017 with OC).")
    return base

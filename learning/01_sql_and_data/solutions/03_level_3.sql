-- Exercise 3.1: Linking Name to Structure
SELECT 
    md.pref_name, 
    md.chembl_id, 
    cs.canonical_smiles
FROM molecule_dictionary md
JOIN compound_structures cs ON md.molregno = cs.molregno
WHERE md.pref_name IN ('IMATINIB', 'ASPIRIN', 'CAFFEINE');

-- Exercise 3.2: "The COX-2 Project"
SELECT 
    md.pref_name AS compound_name, 
    td.pref_name AS target_name, 
    act.standard_value AS ic50_nM
FROM activities act
JOIN molecule_dictionary md ON act.molregno = md.molregno
JOIN target_dictionary td ON act.tid = td.tid
WHERE td.pref_name = 'Cyclooxygenase-2'
  AND act.standard_type = 'IC50'
  AND act.standard_value < 50
LIMIT 100;

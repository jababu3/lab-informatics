-- Exercise 1.1: Find 'Imatinib'
SELECT chembl_id, pref_name, molregno 
FROM molecule_dictionary 
WHERE pref_name = 'IMATINIB';

-- Exercise 1.2: Find 'Plasmodium falciparum' targets
SELECT * 
FROM target_dictionary 
WHERE organism = 'Plasmodium falciparum';

-- Count them if you want:
-- SELECT count(*) FROM target_dictionary WHERE organism = 'Plasmodium falciparum';

-- Exercise 1.3: Structure lookup for Imatinib
-- (Assuming you found molregno = 12431 from Ex 1.1)
SELECT canonical_smiles 
FROM compound_structures 
WHERE molregno = (SELECT molregno FROM molecule_dictionary WHERE pref_name = 'IMATINIB');

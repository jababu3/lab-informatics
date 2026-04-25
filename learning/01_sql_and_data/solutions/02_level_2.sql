-- Exercise 2.1: Heavy Molecules (>500 MW)
SELECT molregno, mw_monoisotopic 
FROM compound_properties 
WHERE mw_monoisotopic > 500 
ORDER BY mw_monoisotopic DESC 
LIMIT 10;

-- Exercise 2.2: Potent Activities (IC50 < 100 nM)
-- Note: 'standard_value' is usually stored as a number, but sometimes text. 
-- In ChEMBL it is numeric.
SELECT * 
FROM activities 
WHERE standard_type = 'IC50' 
  AND standard_value < 100 
LIMIT 50;

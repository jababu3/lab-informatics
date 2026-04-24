# QSAR Tutorial

Train predictive models for compound activity.

## Requirements

- At least 10 compounds with activity data
- Molecular descriptors (auto-calculated)

## Example

```python
import requests

training_data = {
    "compounds": [
        {
            "molecular_weight": 180.16,
            "logp": 1.19,
            "tpsa": 63.6,
            "hbd": 1,
            "hba": 4,
            "rotatable_bonds": 3,
            "activity_value": 7.5  # pIC50
        },
        # ... add 9+ more compounds
    ]
}

response = requests.post(
    "http://localhost:8000/analytics/qsar/train?model_type=random_forest",
    json=training_data
)

result = response.json()
print(f"Test R²: {result['r2_test']:.3f}")
print(f"RMSE: {result['rmse_test']:.3f}")
print("\nTop features:")
for feat in result['feature_importance'][:3]:
    print(f"  {feat['feature']}: {feat['importance']:.3f}")
```

## Interpretation

- R² > 0.7: Good predictive model
- Check feature importance for SAR insights
- Validate with external test set

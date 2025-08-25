# Child Opportunity Index (COI) Integration Plan

## 🎯 Overview

This document outlines the plan to integrate Child Opportunity Index (COI) data into our existing ADI + Distance analysis, creating a comprehensive neighborhood assessment tool that measures both **adult disadvantage** (ADI) and **child opportunity** (COI).

### What is COI?
The Child Opportunity Index measures neighborhood conditions that matter for child development across **three major domains**:
- **Education**: Quality of early childhood, elementary, and secondary education
- **Health & Environment**: Environmental quality, health resources, and safety
- **Social & Economic**: Economic resources, employment, housing, and wealth

### COI + ADI: Perfect Complement
- **ADI**: Measures adult socioeconomic disadvantage (healthcare/research focus)
- **COI**: Measures child development opportunities (family/policy focus)
- **Together**: Comprehensive neighborhood assessment for family-focused research

---

## 📊 Recommended COI Metrics for Integration

Based on analysis of 137+ available COI variables, here are the **most valuable metrics** for research:

### Tier 1: Essential COI Metrics (8 variables)
**Overall Index:**
1. `r_COI_nat` - Child Opportunity Score (National, 1-100)
2. `c5_COI_nat` - Child Opportunity Level (Very Low to Very High)

**Main Domain Scores:**
3. `r_ED_nat` - Education Score (National, 1-100)
4. `r_HE_nat` - Health & Environment Score (National, 1-100) 
5. `r_SE_nat` - Social & Economic Score (National, 1-100)

**Main Domain Levels:**
6. `c5_ED_nat` - Education Level (Very Low to Very High)
7. `c5_HE_nat` - Health & Environment Level (Very Low to Very High)
8. `c5_SE_nat` - Social & Economic Level (Very Low to Very High)

### Tier 2: Key Subdomain Metrics (Optional 6 variables)
**Education Subdomains:**
9. `r_ED_EL_nat` - Elementary Education Score (1-100)
10. `r_ED_ER_nat` - Educational Resources Score (1-100)

**Health & Environment Subdomains:**
11. `r_HE_HR_nat` - Health Resources Score (1-100)
12. `r_HE_HE_nat` - Healthy Environments Score (1-100)

**Social & Economic Subdomains:**
13. `r_SE_ER_nat` - Economic Resources Score (1-100)
14. `r_SE_HQ_nat` - Housing Quality Score (1-100)

### Rationale for Selection:
✅ **Nationally normed** (comparable across all US locations)
✅ **2020 data** (most recent and relevant)
✅ **Research-proven domains** (established in child development literature)
✅ **Interpretable scales** (1-100 scores + categorical levels)
✅ **Policy-relevant** (actionable for intervention research)

---

## 🔧 Technical Implementation

### Geographic Level Challenge
- **COI Data**: Census tract level (11-digit FIPS)
- **ADI Data**: Block group level (12-digit FIPS) 
- **Solution**: Map block groups to parent census tracts

### FIPS Code Mapping Strategy
```python
# Convert 12-digit block group FIPS to 11-digit tract FIPS
def blockgroup_to_tract_fips(bg_fips):
    """Convert block group FIPS (12 digits) to tract FIPS (11 digits)"""
    if len(str(bg_fips)) == 12:
        return str(bg_fips)[:11]  # Remove last digit (block group)
    return str(bg_fips)
```

### Code Integration Points

#### 1. Data Loading (Both Scripts)
```python
# Load COI data
COI_LOOKUP_CSV_PATH = os.path.join(project_root, "data", "reference", "COI", "1_index", "1_index.csv")
coi_df = pd.read_csv(COI_LOOKUP_CSV_PATH)
coi_df = coi_df[coi_df['year'] == 2020]  # Use most recent data
coi_df['tract_fips'] = coi_df['geoid20'].astype(str)
coi_lookup_dict = coi_df.set_index('tract_fips').to_dict('index')
```

#### 2. COI Lookup Function
```python
def lookup_coi_metrics(fips_code):
    """Lookup COI metrics from block group FIPS code"""
    if not fips_code:
        return [None] * 8  # Return None for all COI fields
    
    # Convert block group FIPS to tract FIPS
    tract_fips = blockgroup_to_tract_fips(fips_code)
    
    if tract_fips in coi_lookup_dict:
        coi_data = coi_lookup_dict[tract_fips]
        return [
            coi_data.get('r_COI_nat'),
            coi_data.get('c5_COI_nat'),
            coi_data.get('r_ED_nat'),
            coi_data.get('r_HE_nat'),
            coi_data.get('r_SE_nat'),
            coi_data.get('c5_ED_nat'),
            coi_data.get('c5_HE_nat'),
            coi_data.get('c5_SE_nat')
        ]
    return [None] * 8
```

#### 3. Excel Output with Multi-Sheet Structure
```python
# Create Excel writer with multiple sheets
with pd.ExcelWriter(OUTPUT_EXCEL_FILE_PATH, engine='openpyxl') as writer:
    # Sheet 1: Main results
    data_df.to_excel(writer, sheet_name='Results', index=False)
    
    # Sheet 2: Data dictionary
    data_dict_df.to_excel(writer, sheet_name='Data Dictionary', index=False)
```

---

## 📋 Enhanced Excel Output Structure

### Sheet 1: "Results"
| Column | Description | Source |
|--------|-------------|--------|
| **Original Data** | | |
| MRN | Medical Record Number | Input |
| Address | Original address | Input |
| **Geocoding** | | |
| Longitude | Geocoded longitude | Calculated |
| Latitude | Geocoded latitude | Calculated |
| FIPS | Block group FIPS code | Calculated |
| Geocoding_Method | ADDRFEAT/ZIP_CENTROID | Calculated |
| **Area Deprivation Index** | | |
| ADI_NATRANK | National ADI ranking (1-100) | ADI Dataset |
| ADI_STATERNK | State ADI ranking (1-10) | ADI Dataset |
| **Distance Analysis** | | |
| Distance | Miles to target address | Calculated |
| **Child Opportunity Index** | | |
| COI_Score_National | Overall COI score (1-100) | COI Dataset |
| COI_Level_National | Overall COI level (Very Low-Very High) | COI Dataset |
| COI_Education_Score | Education domain score (1-100) | COI Dataset |
| COI_Health_Environment_Score | Health & Environment score (1-100) | COI Dataset |
| COI_Social_Economic_Score | Social & Economic score (1-100) | COI Dataset |
| COI_Education_Level | Education level (Very Low-Very High) | COI Dataset |
| COI_Health_Environment_Level | Health & Environment level | COI Dataset |
| COI_Social_Economic_Level | Social & Economic level | COI Dataset |

### Sheet 2: "Data Dictionary"
| Variable | Type | Scale | Description | Interpretation | Research Use |
|----------|------|-------|-------------|----------------|--------------|
| ADI_NATRANK | Numeric | 1-100 | National ADI ranking | Higher = more disadvantaged | Health disparities research |
| COI_Score_National | Numeric | 1-100 | National COI score | Higher = more opportunity | Child development research |
| ... | | | | | |

---

## 🎯 Research Applications

### Combined ADI + COI Analysis Enables:

**Healthcare Research:**
- Maternal-child health outcomes by neighborhood opportunity
- Pediatric health disparities across education/economic gradients
- Family access to health resources and educational supports

**Social Services Research:**
- Multi-generational intervention targeting (adults + children)
- Resource allocation based on both current disadvantage and future opportunity
- Policy impact assessment on families

**Academic Research:**
- Neighborhood effects on child development trajectories
- Intergenerational mobility and opportunity structures
- Environmental justice and child health

### Interpretation Framework:
- **High ADI + Low COI**: Immediate need + limited child opportunity
- **High ADI + High COI**: Immediate need + strong child opportunity  
- **Low ADI + Low COI**: Low current need + limited child opportunity
- **Low ADI + High COI**: Low current need + strong child opportunity

---

## 📁 Implementation Checklist

### Phase 1: Core Integration
- [ ] Add COI data loading to both geocoding scripts
- [ ] Implement FIPS tract mapping function
- [ ] Add 8 essential COI variables to output
- [ ] Create multi-sheet Excel output
- [ ] Build comprehensive data dictionary

### Phase 2: Enhanced Features (Optional)
- [ ] Add 6 subdomain COI metrics
- [ ] Create COI + ADI visualization dashboard
- [ ] Add metropolitan area COI scores for urban research
- [ ] Implement COI trend analysis (2012-2020)

### Phase 3: Validation & Documentation
- [ ] Test COI integration with sample data
- [ ] Validate FIPS mapping accuracy
- [ ] Create user guide with research examples
- [ ] Update README with COI capabilities

---

## 🚀 Expected Benefits

**For Researchers:**
✅ **Comprehensive Neighborhood Assessment**: Both adult disadvantage and child opportunity
✅ **Policy-Relevant Metrics**: Actionable domains for intervention research
✅ **Standardized Measures**: Nationally comparable COI + ADI scores
✅ **Multi-Generational Focus**: Perfect for family and community health research

**For Analysis:**
✅ **Enhanced Granularity**: 3 major domains + 6 subdomains of child opportunity
✅ **Complementary Perspectives**: Current disadvantage + future opportunity potential
✅ **Research-Ready Output**: Publication-quality data dictionary and variable selection

---

## 📊 Sample Output Preview

```
Address: 123 Main St, Little Rock, AR 72201
├── Geocoding: 34.7465° N, 92.2896° W (ADDRFEAT method)
├── FIPS: 050190001001 (Block Group) → 05019000100 (Tract)
├── ADI: National=67 (high disadvantage), State=8 (high disadvantage)
├── Distance: 2.3 miles to target
└── COI: Overall=28 (low opportunity), Education=31, Health=25, Social/Economic=26
```

**Interpretation**: This address shows high adult disadvantage (ADI=67) and low child opportunity (COI=28), indicating a neighborhood that would benefit from both immediate health interventions and long-term child development investments.

---

*This plan provides a strategic, research-focused approach to COI integration that enhances our existing ADI analysis capabilities while maintaining usability and research rigor.*
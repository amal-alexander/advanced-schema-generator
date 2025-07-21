import streamlit as st
import json
import csv
import io
import re
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Advanced Schema Generator Pro",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .schema-container {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #007bff;
        margin: 1rem 0;
    }
    .property-group {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #e9ecef;
    }
    .bulk-stats {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
    }
    .schema-preview {
        max-height: 400px;
        overflow-y: auto;
        background: #2d3748;
        color: #e2e8f0;
        padding: 1rem;
        border-radius: 5px;
        font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    }
</style>
""", unsafe_allow_html=True)

# Schema Type Definitions with their properties
SCHEMA_DEFINITIONS = {
    "Article": {
        "required": ["headline", "author", "datePublished"],
        "common": ["description", "url", "image", "wordCount", "articleSection", "articleBody"],
        "advanced": ["about", "mentions", "isPartOf", "mainEntity", "speakable", "significantLink"]
    },
    "WebPage": {
        "required": ["name", "url"],
        "common": ["description", "author", "datePublished", "dateModified", "breadcrumb"],
        "advanced": ["about", "mentions", "isPartOf", "mainEntity", "significantLink", "relatedLink"]
    },
    "Person": {
        "required": ["name"],
        "common": ["url", "image", "description", "jobTitle", "worksFor", "birthDate"],
        "advanced": ["knowsAbout", "sameAs", "memberOf", "alumniOf", "award", "owns"]
    },
    "Organization": {
        "required": ["name"],
        "common": ["url", "logo", "description", "address", "contactPoint", "foundingDate"],
        "advanced": ["sameAs", "parentOrganization", "subOrganization", "member", "owns", "sponsor"]
    },
    "Event": {
        "required": ["name", "startDate"],
        "common": ["description", "location", "organizer", "endDate", "eventStatus", "eventAttendanceMode"],
        "advanced": ["about", "performer", "sponsor", "subEvent", "superEvent", "workPerformed"]
    },
    "FAQPage": {
        "required": ["mainEntity"],
        "common": ["name", "description", "url", "datePublished", "author"],
        "advanced": ["about", "mentions", "isPartOf", "significantLink"]
    },
    "Product": {
        "required": ["name"],
        "common": ["description", "image", "brand", "offers", "review", "aggregateRating"],
        "advanced": ["about", "isRelatedTo", "isSimilarTo", "category", "manufacturer", "model"]
    },
    "Recipe": {
        "required": ["name", "recipeIngredient", "recipeInstructions"],
        "common": ["description", "image", "author", "datePublished", "prepTime", "cookTime"],
        "advanced": ["about", "recipeCategory", "recipeCuisine", "nutrition", "suitableForDiet", "recipeYield"]
    },
    "LocalBusiness": {
        "required": ["name", "address"],
        "common": ["description", "url", "telephone", "openingHours", "priceRange", "image"],
        "advanced": ["sameAs", "parentOrganization", "paymentAccepted", "currenciesAccepted", "areaServed"]
    },
    "Course": {
        "required": ["name", "provider"],
        "common": ["description", "url", "courseCode", "instructor", "educationalLevel"],
        "advanced": ["about", "teaches", "coursePrerequisites", "hasCourseInstance", "aggregateRating"]
    }
}

# Property type mappings for better input handling
PROPERTY_TYPES = {
    "text": ["name", "headline", "description", "jobTitle", "brand"],
    "url": ["url", "image", "logo", "sameAs"],
    "date": ["datePublished", "dateModified", "startDate", "endDate", "birthDate", "foundingDate"],
    "number": ["wordCount", "prepTime", "cookTime"],
    "array": ["recipeIngredient", "recipeInstructions", "sameAs", "about", "mentions"],
    "object": ["author", "organizer", "location", "offers", "address", "contactPoint"]
}

def get_property_type(prop_name: str) -> str:
    """Determine the appropriate input type for a property"""
    for prop_type, props in PROPERTY_TYPES.items():
        if prop_name in props:
            return prop_type
    return "text"

def create_dynamic_input(prop_name: str, prop_type: str, key_suffix: str = "") -> Any:
    """Create appropriate input widget based on property type"""
    key = f"{prop_name}_{key_suffix}"
    
    if prop_type == "url":
        return st.text_input(f"🔗 {prop_name}", placeholder="https://example.com", key=key)
    elif prop_type == "date":
        return st.date_input(f"📅 {prop_name}", key=key)
    elif prop_type == "number":
        return st.number_input(f"🔢 {prop_name}", min_value=0, key=key)
    elif prop_type == "array":
        return st.text_area(f"📋 {prop_name} (one per line)", 
                           placeholder="Enter each item on a new line", key=key)
    elif prop_type == "object":
        return st.text_area(f"🏗️ {prop_name} (JSON format)", 
                           placeholder='{"@type": "Person", "name": "John Doe"}', key=key)
    else:
        return st.text_input(f"📝 {prop_name}", key=key)

def process_property_value(value: Any, prop_type: str) -> Any:
    """Process property value based on its type"""
    if not value:
        return None
        
    if prop_type == "array":
        if isinstance(value, str):
            return [item.strip() for item in value.split('\n') if item.strip()]
        return value
    elif prop_type == "object":
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return {"name": value}  # Fallback
        return value
    elif prop_type == "date":
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        return str(value)
    else:
        return value

def generate_schema(schema_type: str, properties: Dict[str, Any], id_value: str = None) -> Dict[str, Any]:
    """Generate a complete schema object"""
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type
    }
    
    if id_value:
        schema["@id"] = id_value
    
    # Process properties
    for prop_name, prop_value in properties.items():
        if prop_value is not None:
            prop_type = get_property_type(prop_name)
            processed_value = process_property_value(prop_value, prop_type)
            if processed_value is not None:
                schema[prop_name] = processed_value
    
    return schema

def validate_schema(schema: Dict[str, Any], schema_type: str) -> List[str]:
    """Validate schema against requirements"""
    errors = []
    required_props = SCHEMA_DEFINITIONS.get(schema_type, {}).get("required", [])
    
    for required_prop in required_props:
        if required_prop not in schema or not schema[required_prop]:
            errors.append(f"Missing required property: {required_prop}")
    
    return errors

def process_bulk_data(data: List[Dict], schema_type: str) -> List[Dict]:
    """Process bulk data into schema objects"""
    schemas = []
    
    for i, row in enumerate(data):
        try:
            schema = generate_schema(schema_type, row, row.get('@id'))
            validation_errors = validate_schema(schema, schema_type)
            
            if validation_errors:
                st.warning(f"Row {i+1} validation issues: {', '.join(validation_errors)}")
            
            schemas.append(schema)
        except Exception as e:
            st.error(f"Error processing row {i+1}: {str(e)}")
    
    return schemas

# Main App
def main():
    st.title("🧠 Advanced Schema Generator Pro")
    st.markdown("""
    Generate powerful Schema.org markup with dynamic field detection, bulk processing, 
    and advanced property handling. Perfect for SEO professionals and developers.
    """)
    
    # Mode Selection
    mode = st.radio("Select Mode", ["Single Schema", "Bulk Processing", "Template Generator"], horizontal=True)
    
    if mode == "Single Schema":
        render_single_schema_mode()
    elif mode == "Bulk Processing":
        render_bulk_processing_mode()
    else:
        render_template_generator_mode()

def render_single_schema_mode():
    """Render single schema generation interface"""
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("⚙️ Schema Configuration")
        
        # Schema type selection
        schema_type = st.selectbox("Select Schema Type", list(SCHEMA_DEFINITIONS.keys()))
        schema_def = SCHEMA_DEFINITIONS[schema_type]
        
        # ID field
        id_value = st.text_input("@id (optional)", placeholder="https://example.com/#schema")
        
        st.markdown("---")
        
        # Dynamic property sections
        properties = {}
        
        # Required properties
        if schema_def["required"]:
            st.markdown("### 🔴 Required Properties")
            for prop in schema_def["required"]:
                prop_type = get_property_type(prop)
                value = create_dynamic_input(prop, prop_type, "required")
                if value:
                    properties[prop] = value
        
        # Common properties
        if schema_def["common"]:
            st.markdown("### 🟡 Common Properties")
            selected_common = st.multiselect("Select common properties to include", 
                                           schema_def["common"])
            for prop in selected_common:
                prop_type = get_property_type(prop)
                value = create_dynamic_input(prop, prop_type, "common")
                if value:
                    properties[prop] = value
        
        # Advanced properties
        if schema_def["advanced"]:
            st.markdown("### 🟢 Advanced Properties")
            selected_advanced = st.multiselect("Select advanced properties to include", 
                                             schema_def["advanced"])
            for prop in selected_advanced:
                prop_type = get_property_type(prop)
                value = create_dynamic_input(prop, prop_type, "advanced")
                if value:
                    properties[prop] = value
        
        # Custom properties
        st.markdown("### ⚡ Custom Properties")
        custom_props = st.text_area("Add custom properties (JSON format)", 
                                   placeholder='{"customProp": "value", "anotherProp": ["item1", "item2"]}')
        if custom_props:
            try:
                custom_data = json.loads(custom_props)
                properties.update(custom_data)
            except:
                st.error("Invalid JSON format in custom properties")
    
    with col2:
        st.subheader("📤 Generated Schema")
        
        # Generate schema
        schema = generate_schema(schema_type, properties, id_value)
        
        # Validation
        validation_errors = validate_schema(schema, schema_type)
        if validation_errors:
            st.error("Validation Issues:")
            for error in validation_errors:
                st.write(f"• {error}")
        else:
            st.success("✅ Schema validation passed!")
        
        # Schema output
        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
        
        # Tabs for different outputs
        tab1, tab2, tab3 = st.tabs(["JSON-LD", "HTML Script", "Microdata"])
        
        with tab1:
            st.code(schema_json, language="json")
            st.download_button("📥 Download JSON-LD", schema_json, 
                             f"schema_{schema_type.lower()}.json", "application/json")
        
        with tab2:
            html_output = f'<script type="application/ld+json">\n{schema_json}\n</script>'
            st.code(html_output, language="html")
            st.download_button("📥 Download HTML", html_output, 
                             f"schema_{schema_type.lower()}.html", "text/html")
        
        with tab3:
            st.info("Microdata conversion coming soon!")

def render_bulk_processing_mode():
    """Render bulk processing interface"""
    
    st.subheader("📊 Bulk Schema Generation")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📥 Data Input")
        
        # Schema type for bulk processing
        schema_type = st.selectbox("Select Schema Type for Bulk", list(SCHEMA_DEFINITIONS.keys()))
        
        # Input method selection
        input_method = st.radio("Choose input method", 
                               ["Upload CSV", "Paste JSON", "Manual Entry"])
        
        bulk_data = []
        
        if input_method == "Upload CSV":
            uploaded_file = st.file_uploader("Upload CSV file", type=['csv'])
            if uploaded_file:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df.head())
                bulk_data = df.to_dict('records')
                
        elif input_method == "Paste JSON":
            json_input = st.text_area("Paste JSON array", 
                                     placeholder='[{"name": "Item 1", "description": "..."}, {"name": "Item 2", "description": "..."}]',
                                     height=200)
            if json_input:
                try:
                    bulk_data = json.loads(json_input)
                except:
                    st.error("Invalid JSON format")
                    
        else:  # Manual Entry
            num_items = st.number_input("Number of items", min_value=1, max_value=50, value=3)
            bulk_data = []
            
            for i in range(num_items):
                st.markdown(f"#### Item {i+1}")
                item_data = {}
                
                # Required fields for manual entry
                schema_def = SCHEMA_DEFINITIONS[schema_type]
                for prop in schema_def["required"]:
                    value = st.text_input(f"{prop}", key=f"manual_{prop}_{i}")
                    if value:
                        item_data[prop] = value
                
                if item_data:
                    bulk_data.append(item_data)
    
    with col2:
        st.markdown("### 📤 Bulk Output")
        
        if bulk_data:
            # Process bulk data
            schemas = process_bulk_data(bulk_data, schema_type)
            
            # Stats
            st.markdown(f"""
            <div class="bulk-stats">
                <h3>📈 Processing Stats</h3>
                <p><strong>{len(schemas)}</strong> schemas generated</p>
                <p><strong>{schema_type}</strong> schema type</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Output format selection
            output_format = st.selectbox("Output format", 
                                       ["Individual JSON files (ZIP)", "Combined JSON array", "HTML script tags"])
            
            if st.button("🚀 Generate Bulk Schemas"):
                if output_format == "Individual JSON files (ZIP)":
                    # Create ZIP file
                    import zipfile
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                        for i, schema in enumerate(schemas):
                            schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
                            filename = f"schema_{i+1}_{schema_type.lower()}.json"
                            zip_file.writestr(filename, schema_json)
                    
                    st.download_button("📥 Download ZIP", zip_buffer.getvalue(), 
                                     f"bulk_schemas_{schema_type.lower()}.zip", "application/zip")
                
                elif output_format == "Combined JSON array":
                    combined_json = json.dumps(schemas, indent=2, ensure_ascii=False)
                    st.code(combined_json, language="json")
                    st.download_button("📥 Download Combined JSON", combined_json, 
                                     f"bulk_schemas_{schema_type.lower()}.json", "application/json")
                
                else:  # HTML script tags
                    html_output = ""
                    for i, schema in enumerate(schemas):
                        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
                        html_output += f'<!-- Schema {i+1} -->\n<script type="application/ld+json">\n{schema_json}\n</script>\n\n'
                    
                    st.code(html_output, language="html")
                    st.download_button("📥 Download HTML", html_output, 
                                     f"bulk_schemas_{schema_type.lower()}.html", "text/html")

def render_template_generator_mode():
    """Render template generator interface"""
    
    st.subheader("📋 Template Generator")
    st.markdown("Generate CSV templates for bulk processing or JSON templates for development.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### ⚙️ Template Configuration")
        
        schema_type = st.selectbox("Select Schema Type for Template", list(SCHEMA_DEFINITIONS.keys()))
        schema_def = SCHEMA_DEFINITIONS[schema_type]
        
        include_required = st.checkbox("Include required properties", value=True)
        include_common = st.checkbox("Include common properties", value=True)
        include_advanced = st.checkbox("Include advanced properties", value=False)
        include_examples = st.checkbox("Include example values", value=True)
        
        template_format = st.radio("Template format", ["CSV", "JSON", "Excel"])
    
    with col2:
        st.markdown("### 📤 Generated Template")
        
        # Build template structure
        template_props = []
        
        if include_required:
            template_props.extend(schema_def["required"])
        if include_common:
            template_props.extend(schema_def["common"])
        if include_advanced:
            template_props.extend(schema_def["advanced"])
        
        # Remove duplicates while preserving order
        template_props = list(dict.fromkeys(template_props))
        
        if template_format == "CSV":
            # Create CSV template
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            
            # Headers
            headers = ["@id"] + template_props
            writer.writerow(headers)
            
            # Example rows if requested
            if include_examples:
                example_row = ["https://example.com/#schema1"]
                for prop in template_props:
                    if prop == "name":
                        example_row.append("Example Name")
                    elif prop == "description":
                        example_row.append("Example description")
                    elif prop == "url":
                        example_row.append("https://example.com")
                    elif get_property_type(prop) == "date":
                        example_row.append("2024-01-01")
                    elif get_property_type(prop) == "array":
                        example_row.append("item1|item2|item3")
                    else:
                        example_row.append("example value")
                writer.writerow(example_row)
            
            csv_content = csv_buffer.getvalue()
            st.text_area("CSV Template", csv_content, height=200)
            st.download_button("📥 Download CSV Template", csv_content, 
                             f"template_{schema_type.lower()}.csv", "text/csv")
        
        elif template_format == "JSON":
            # Create JSON template
            template_obj = {"@context": "https://schema.org", "@type": schema_type}
            
            for prop in template_props:
                if include_examples:
                    if prop == "name":
                        template_obj[prop] = "Example Name"
                    elif prop == "description":
                        template_obj[prop] = "Example description"
                    elif get_property_type(prop) == "array":
                        template_obj[prop] = ["example item 1", "example item 2"]
                    elif get_property_type(prop) == "object":
                        template_obj[prop] = {"@type": "Thing", "name": "Example Object"}
                    else:
                        template_obj[prop] = "example value"
                else:
                    template_obj[prop] = ""
            
            json_template = json.dumps([template_obj], indent=2, ensure_ascii=False)
            st.code(json_template, language="json")
            st.download_button("📥 Download JSON Template", json_template, 
                             f"template_{schema_type.lower()}.json", "application/json")

if __name__ == "__main__":
    main()
"""Post-processing hooks for drf-spectacular schema generation."""


def postprocess_schema_enums(result, generator, request, public):
    """
    Post-process the generated schema to fix enum naming collisions.
    
    Maps auto-generated Status enum collisions to unique, descriptive names.
    """
    if "components" not in result or "schemas" not in result["components"]:
        return result

    schemas = result["components"]["schemas"]
    enum_mapping = {}
    
    # Map auto-generated enum names to descriptive ones
    # These correspond to the Status fields from different models
    enum_renames = {
        "Status1a6Enum": "ContactSubmissionStatus",  # ContactSubmission.Status
        "InvoiceStatusStatusEnum": "InvoicePaymentStatus",  # Invoice.Status  
        "StatusEnum": "PaymentProcessingStatus",  # Payment.Status
    }
    
    # Find and rename enums
    for old_name, new_name in enum_renames.items():
        if old_name in schemas:
            schemas[new_name] = schemas.pop(old_name)
            enum_mapping[old_name] = new_name
    
    # Update all references to renamed enums
    def update_refs(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "$ref" and isinstance(value, str):
                    for old_name, new_name in enum_mapping.items():
                        if f"#/components/schemas/{old_name}" in value:
                            obj[key] = value.replace(old_name, new_name)
                else:
                    update_refs(value)
        elif isinstance(obj, list):
            for item in obj:
                update_refs(item)
    
    update_refs(result)
    return result

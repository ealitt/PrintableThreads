"""Apply validation differs from standalone fastener validation."""
def validate_applied(body, original_regions, joining):
    if not body or not body.isSolid or body.volume<=0 or body.lumps.count<1:
        raise ValueError('Applying this thread did not leave a closed solid. Reduce Section size or select a thicker cylindrical region.')
    if joining and body.lumps.count>original_regions:
        raise ValueError('Some thread fragments do not touch the selected part. Reduce 3D print tolerance or Section size, or apply to a smaller cylindrical region.')
    # Cuts on thin or interrupted parts may split material into several solids.
    return body

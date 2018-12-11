line = context
delivery = line.getParentValue()
if delivery.getPortalType() != "Purchase Packing List":
  return None
section = delivery.getSourceSectionValue()
source_currency = delivery.getPriceCurrencyValue()
return line.Base_getAssetPrice(
  section = section,
  source_currency = source_currency,
  delivery = delivery)

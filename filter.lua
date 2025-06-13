function envoy_on_request(request_handle)
  local priority = request_handle:headers():get("x-priority")
  local overloaded = request_handle:headers():get("x-overloaded") ~= nil and
      request_handle:headers():get("x-overloaded") ~= "0"
  if priority == "p3" then
    -- If overloaded P3 gets rejected immediately
    if overloaded then
      request_handle:respond({ [":status"] = "429" }, "Overloaded")
    else
      -- Otherwise P3 uses pt_only backends
      request_handle:streamInfo():dynamicMetadata():set("envoy.lb", "pt_only", "true")
    end
  elseif priority == "p2" then
    -- If not overloaded P2 traffic gets to use PT and OD endpoints
    if overloaded ~= true then
      request_handle:streamInfo():dynamicMetadata():set("envoy.lb", "pt_od", "true")
    else
      -- Otherwise it only uses OD
      request_handle:streamInfo():dynamicMetadata():set("envoy.lb", "od_only", "true")
    end
  else
    -- P1 traffic always uses all endpoints
    request_handle:streamInfo():dynamicMetadata():set("envoy.lb", "pt_od", "true")
  end
end

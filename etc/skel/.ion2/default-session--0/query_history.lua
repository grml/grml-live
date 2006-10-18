local saves={
    "y",
    "firefox",
    "y",
    "",
    "firefox",
    "",
    "WFloatWS",
    "floating",
    "",
    "browse",
}
for k=table.getn(saves),1,-1 do query_history_push(saves[k]) end

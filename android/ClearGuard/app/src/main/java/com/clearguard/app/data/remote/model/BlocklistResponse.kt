package com.clearguard.app.data.remote.model

import com.google.gson.annotations.SerializedName

data class BlocklistResponse(
    @SerializedName("version") val version: String,
    @SerializedName("domains") val domains: List<String>,
    @SerializedName("total_count") val totalCount: Int
)

package com.clearguard.app.data.remote

import com.clearguard.app.data.remote.model.BlocklistResponse
import retrofit2.http.GET

interface ClearGuardApi {
    @GET("api/v1/blocklist")
    suspend fun getBlocklist(): BlocklistResponse
}

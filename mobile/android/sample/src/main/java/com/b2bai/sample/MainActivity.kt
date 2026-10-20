package com.b2bai.sample

import android.graphics.Color
import android.os.Bundle
import android.widget.FrameLayout
import androidx.appcompat.app.AppCompatActivity
import com.b2bai.sdk.AgentBubble

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = FrameLayout(this)
        root.setBackgroundColor(Color.parseColor("#F7F7F8"))
        setContentView(root)
        AgentBubble(
            activity = this,
            apiBase = "http://10.0.2.2:8000",
            tenantId = "ananas",
            tenantKey = "pk_ananas_demo",
        ).attach(root)
    }
}

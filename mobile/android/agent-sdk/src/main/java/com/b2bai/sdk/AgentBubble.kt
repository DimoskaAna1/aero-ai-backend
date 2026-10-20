package com.b2bai.sdk

import android.Manifest
import android.animation.Animator
import android.animation.AnimatorListenerAdapter
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID
import java.util.concurrent.Executors

/**
 * Floating bubble for a host Android app. It posts to the same chat API as the web widget.
 */
class AgentBubble(
    private val activity: Activity,
    private val apiBase: String,
    private val tenantId: String,
    private val tenantKey: String,
) {
    private val sessionId = "sess_" + UUID.randomUUID().toString().replace("-", "").take(16)
    private val executor = Executors.newSingleThreadExecutor()
    private var panel: LinearLayout? = null
    private var thread: LinearLayout? = null
    private var scroller: ScrollView? = null
    private var field: EditText? = null
    private var launcher: Button? = null
    private var sending = false
    private var greeting = "Zdravo. Prasaj za proizvod, cena ili termin."
    private var agentName = "Ana"
    private var opening = emptyList<Choice>()
    private val history = mutableListOf<Line>()

    fun attach(root: FrameLayout) {
        val bubble = Button(activity).apply {
            text = "Ana"
            setTextColor(Color.parseColor("#041018"))
            setTypeface(typeface, Typeface.BOLD)
            background = circle("#38BDF8")
            stateListAnimator = null
            elevation = dp(8).toFloat()
            setOnClickListener {
                animate().scaleX(0.92f).scaleY(0.92f).setDuration(80).withEndAction {
                    animate().scaleX(1f).scaleY(1f).setDuration(180).start()
                }.start()
                toggle(root)
            }
        }
        val params = FrameLayout.LayoutParams(dp(64), dp(64)).apply {
            gravity = Gravity.END or Gravity.BOTTOM
            setMargins(0, 0, dp(20), dp(24))
        }
        root.addView(bubble, params)
        launcher = bubble
        executor.execute { loadConfig() }
    }

    private fun toggle(root: FrameLayout) {
        val existing = panel
        if (existing != null) {
            close(root, existing)
            return
        }
        open(root)
    }

    private fun open(root: FrameLayout) {
        val box = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = rounded("#F7F7F8", dp(28))
            elevation = dp(16).toFloat()
            alpha = 0f
            translationY = dp(28).toFloat()
        }
        val header = TextView(activity).apply {
            text = agentName
            setTextColor(Color.parseColor("#161616"))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 16f)
            setTypeface(typeface, Typeface.BOLD)
        }
        val messages = LinearLayout(activity).apply { orientation = LinearLayout.VERTICAL }
        val scroll = ScrollView(activity).apply {
            isFillViewport = true
            addView(messages)
        }
        val input = EditText(activity).apply {
            hint = "Message Ana"
            setTextColor(Color.parseColor("#161616"))
            setHintTextColor(Color.parseColor("#9CA3AF"))
            background = rounded("#FFFFFF", dp(16))
            setPadding(dp(14), dp(12), dp(14), dp(12))
        }
        val row = LinearLayout(activity).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(8), 0, 0)
        }
        val mic = pill("Mic", "#FFFFFF", "#161616") { listen() }
        val send = pill("Send", "#111111", "#FFFFFF") {
            val text = input.text.toString().trim()
            if (text.isNotEmpty()) {
                input.setText("")
                ask(text)
            }
        }
        row.addView(input, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        row.addView(space())
        row.addView(mic)
        row.addView(space())
        row.addView(send)
        box.addView(header)
        box.addView(scroll, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(320)))
        box.addView(row)
        val width = minOf(root.width - dp(32), dp(360)).coerceAtLeast(dp(280))
        val params = FrameLayout.LayoutParams(width, FrameLayout.LayoutParams.WRAP_CONTENT).apply {
            gravity = Gravity.END or Gravity.BOTTOM
            setMargins(dp(16), dp(16), dp(16), dp(104))
        }
        root.addView(box, params)
        box.animate().alpha(1f).translationY(0f).setDuration(320)
            .setInterpolator(DecelerateInterpolator()).start()
        panel = box
        thread = messages
        scroller = scroll
        field = input
        if (history.isEmpty()) {
            addAssistant(greeting, opening)
        } else {
            history.forEach { line ->
                when (line) {
                    is Line.User -> renderUser(line.text)
                    is Line.Bot -> renderAssistant(line.text, line.choices)
                }
            }
        }
    }

    private fun close(root: FrameLayout, box: View) {
        box.animate().alpha(0f).translationY(dp(24).toFloat()).setDuration(180)
            .setListener(object : AnimatorListenerAdapter() {
                override fun onAnimationEnd(animation: Animator) {
                    root.removeView(box)
                }
            }).start()
        panel = null
        thread = null
        scroller = null
        field = null
    }

    private fun ask(text: String) {
        if (sending) return
        sending = true
        addUser(text)
        val typing = renderAssistant("...", emptyList())
        executor.execute {
            val reply = postChat(text)
            activity.runOnUiThread {
                thread?.removeView(typing)
                addAssistant(reply.text, reply.choices)
                sending = false
            }
        }
    }

    private fun addUser(text: String) {
        history.add(Line.User(text))
        renderUser(text)
    }

    private fun renderUser(text: String) {
        val bubble = TextView(activity).apply {
            this.text = text
            setTextColor(Color.WHITE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            background = rounded("#111111", dp(18))
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        val row = LinearLayout(activity).apply {
            gravity = Gravity.END
            setPadding(dp(36), dp(8), 0, 0)
            addView(bubble)
        }
        thread?.addView(row)
        scrollDown()
    }

    private fun addAssistant(text: String, choices: List<Choice>): View {
        history.add(Line.Bot(text, choices))
        return renderAssistant(text, choices)
    }

    private fun renderAssistant(text: String, choices: List<Choice>): View {
        val column = LinearLayout(activity).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, dp(8), dp(24), 0)
        }
        val bubble = TextView(activity).apply {
            this.text = text
            setTextColor(Color.parseColor("#161616"))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
            background = rounded("#FFFFFF", dp(18))
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        column.addView(bubble)
        if (choices.isNotEmpty()) {
            val chips = LinearLayout(activity).apply { orientation = LinearLayout.HORIZONTAL }
            choices.forEach { choice ->
                val chip = pill(choice.label, "#FFFFFF", "#161616") { ask(choice.message) }
                val gap = LinearLayout.LayoutParams(LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT)
                gap.marginEnd = dp(8)
                chips.addView(chip, gap)
            }
            val scroller = HorizontalScrollView(activity).apply {
                isHorizontalScrollBarEnabled = false
                setPadding(0, dp(8), 0, 0)
                addView(chips)
            }
            column.addView(scroller)
        }
        thread?.addView(column)
        scrollDown()
        return column
    }

    private fun scrollDown() {
        scroller?.post { scroller?.fullScroll(View.FOCUS_DOWN) }
    }

    private fun loadConfig() {
        val connection = open("/api/v1/tenant-config/" + tenantId, "GET") ?: return
        try {
            if (connection.responseCode !in 200..299) return
            val json = JSONObject(connection.inputStream.bufferedReader().readText())
            val name = json.optString("agent_name").ifBlank { agentName }
            val hello = json.optString("greeting_message").ifBlank { greeting }
            val chips = readChoices(json.optJSONArray("quick_chips"))
            activity.runOnUiThread {
                agentName = name.substringBefore("|").trim().ifBlank { "Ana" }
                greeting = hello
                opening = chips
                launcher?.text = agentName
            }
        } catch (_: Exception) {
        } finally {
            connection.disconnect()
        }
    }

    private fun postChat(text: String): Reply {
        val connection = open("/api/v1/chat", "POST")
            ?: return Reply("The assistant is unavailable right now.", emptyList())
        return try {
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("X-Tenant-Id", tenantId)
            connection.setRequestProperty("X-Tenant-Key", tenantKey)
            connection.doOutput = true
            val body = JSONObject()
                .put("tenant_id", tenantId)
                .put("user_message", text)
                .put("session_id", sessionId)
            connection.outputStream.use { it.write(body.toString().toByteArray()) }
            val stream = if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream
            val json = JSONObject(stream.bufferedReader().readText())
            val message = json.optString("assistant_message", json.optString("detail", "The assistant is unavailable right now."))
            Reply(message, readChoices(json.optJSONArray("suggestions")))
        } catch (_: Exception) {
            Reply("The assistant is unavailable right now.", emptyList())
        } finally {
            connection.disconnect()
        }
    }

    private fun readChoices(array: JSONArray?): List<Choice> {
        if (array == null) return emptyList()
        val choices = mutableListOf<Choice>()
        for (index in 0 until array.length()) {
            val item = array.optJSONObject(index) ?: continue
            val label = item.optString("label")
            if (label.isBlank()) continue
            val message = item.optString("message").ifBlank { label }
            choices.add(Choice(label, message))
        }
        return choices
    }

    private fun open(path: String, method: String): HttpURLConnection? {
        return try {
            (URL(apiBase.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
                requestMethod = method
                connectTimeout = 15000
                readTimeout = 30000
            }
        } catch (_: Exception) {
            null
        }
    }

    private fun listen() {
        if (ContextCompat.checkSelfPermission(activity, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(activity, arrayOf(Manifest.permission.RECORD_AUDIO), 41)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(activity)) return
        val recognizer = SpeechRecognizer.createSpeechRecognizer(activity)
        recognizer.setRecognitionListener(object : RecognitionListener {
            override fun onResults(results: Bundle?) {
                val said = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                if (said.isNotBlank()) ask(said)
                recognizer.destroy()
            }
            override fun onError(error: Int) { recognizer.destroy() }
            override fun onReadyForSpeech(params: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "mk-MK")
        }
        recognizer.startListening(intent)
    }

    private fun pill(label: String, fill: String, ink: String, onClick: () -> Unit): Button {
        return Button(activity).apply {
            text = label
            setTextColor(Color.parseColor(ink))
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 13f)
            background = rounded(fill, dp(14))
            stateListAnimator = null
            minimumHeight = dp(44)
            setPadding(dp(14), 0, dp(14), 0)
            setOnClickListener { onClick() }
        }
    }

    private fun space(): View {
        return View(activity).apply {
            layoutParams = LinearLayout.LayoutParams(dp(8), 1)
        }
    }

    private fun dp(value: Int): Int {
        return TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP,
            value.toFloat(),
            activity.resources.displayMetrics,
        ).toInt()
    }

    private fun circle(color: String): GradientDrawable {
        return GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.parseColor(color))
        }
    }

    private fun rounded(color: String, radius: Int): GradientDrawable {
        return GradientDrawable().apply {
            cornerRadius = radius.toFloat()
            setColor(Color.parseColor(color))
        }
    }

    private data class Choice(val label: String, val message: String)
    private data class Reply(val text: String, val choices: List<Choice>)
    private sealed class Line {
        data class User(val text: String) : Line()
        data class Bot(val text: String, val choices: List<Choice>) : Line()
    }
}

<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;

class HmiController extends Controller
{
    private function baseUrl(): string { return rtrim(config('services.ai.url', env('AI_SERVICE_URL', 'http://127.0.0.1:8000')), '/'); }

    public function live() {
        try { return response()->json(Http::timeout(2)->get($this->baseUrl().'/state')->json() ?? []); }
        catch (\Throwable) { return response()->json(['offline'=>true,'message'=>'AI advisory offline'], 503); }
    }

    public function page() { return view('hmi.overview'); }
    public function tank(string $id) { return view('hmi.tank', ['tankId'=>$id]); }
    public function pipeline() { return view('hmi.pipeline'); }
    public function alarms() { return view('hmi.alarms'); }
    public function playground() { return view('hmi.playground'); }
    public function scenarios() { return view('hmi.scenarios'); }
    public function assets() { return view('hmi.assets'); }
    public function settings() { return view('hmi.settings'); }
    public function audit() { return view('hmi.audit'); }

    public function proxyPost(Request $request, string $path) {
        $request->validate(['*'=>'nullable']);
        $response = Http::timeout(5)->post($this->baseUrl().'/'.ltrim($path,'/'), $request->except(['_token']));
        return response()->json($response->json(), $response->status());
    }

    public function control(Request $request) {
        $validated = $request->validate(['ambient_c'=>'nullable|numeric|between:-10,60','solar_gain_c'=>'nullable|numeric|between:0,8','tanks'=>'nullable|array','pipeline'=>'nullable|array','leaks'=>'nullable|array','sensor_faults'=>'nullable|array']);
        $response = Http::timeout(5)->post($this->baseUrl().'/sim/control', $validated);
        return response()->json($response->json(), $response->status());
    }

    public function speed(Request $request) {
        $validated = $request->validate(['factor'=>'required|integer|in:1,10,60,600']);
        $response = Http::timeout(5)->post($this->baseUrl().'/sim/speed', $validated);
        return response()->json($response->json(), $response->status());
    }

    public function reset(Request $request) {
        $response = Http::timeout(5)->post($this->baseUrl().'/sim/reset', ['seed'=>$request->integer('seed',42)]);
        return response()->json($response->json(), $response->status());
    }

    public function scenario(string $name) {
        $response = Http::timeout(5)->post($this->baseUrl().'/sim/scenario/'.urlencode($name));
        return response()->json($response->json(), $response->status());
    }

    public function ack(string $id) {
        $response = Http::timeout(5)->post($this->baseUrl().'/alarms/'.urlencode($id).'/ack', ['user'=>'Demo Operator']);
        return response()->json($response->json(), $response->status());
    }

    public function shelve(Request $request, string $id) {
        $validated = $request->validate(['reason'=>'required|string|max:500','duration_min'=>'required|integer|between:1,480']);
        $response = Http::timeout(5)->post($this->baseUrl().'/alarms/'.urlencode($id).'/shelve', $validated);
        return response()->json($response->json(), $response->status());
    }

    public function ingest(Request $request) {
        $secret = env('SHARED_SECRET','dev-secret');
        $signature = 'sha256='.hash_hmac('sha256',$request->getContent(),$secret);
        if (!hash_equals($signature, $request->header('X-Signature',''))) return response()->json(['error'=>'invalid signature'],403);
        return response()->json(['status'=>'stored']);
    }
}

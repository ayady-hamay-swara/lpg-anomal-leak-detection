<?php

use App\Http\Controllers\HmiController;
use Illuminate\Support\Facades\Route;

Route::get('/dashboard', fn () => redirect()->route('overview'))->name('dashboard');
Route::get('/', [HmiController::class,'page'])->name('overview');

Route::get('/tanks/{id}', [HmiController::class,'tank'])->name('tanks.show');
Route::get('/pipeline', [HmiController::class,'pipeline'])->name('pipeline');
Route::get('/alarms', [HmiController::class,'alarms'])->name('alarms');
Route::get('/playground', [HmiController::class,'playground'])->name('playground');
Route::get('/scenarios', [HmiController::class,'scenarios'])->name('scenarios');
Route::get('/assets', [HmiController::class,'assets'])->name('assets');
Route::get('/settings', [HmiController::class,'settings'])->name('settings');
Route::get('/audit', [HmiController::class,'audit'])->name('audit');

Route::get('/api/live', [HmiController::class,'live']);
Route::post('/api/playground/control', [HmiController::class,'control']);
Route::post('/api/playground/scenario/{name}', [HmiController::class,'scenario']);
Route::post('/api/playground/reset', [HmiController::class,'reset']);
Route::post('/api/playground/speed', [HmiController::class,'speed']);
Route::post('/api/alarms/{id}/ack', [HmiController::class,'ack']);
Route::post('/api/alarms/{id}/shelve', [HmiController::class,'shelve']);

Route::post('/api/ingest/event', [HmiController::class,'ingest']);

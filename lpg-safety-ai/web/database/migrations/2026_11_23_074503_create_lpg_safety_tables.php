<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::table('users', function (Blueprint $table) {
            $table->string('role')->default('operator');
            $table->string('telegram_chat_id')->nullable();
        });
        Schema::create('alarms', function (Blueprint $table) {
            $table->id(); $table->string('alarm_uid')->unique(); $table->string('tag'); $table->string('kind');
            $table->string('priority'); $table->string('state'); $table->text('message'); $table->text('action')->nullable();
            $table->timestamp('raised_at')->nullable(); $table->timestamp('acked_at')->nullable();
            $table->string('acked_by')->nullable(); $table->timestamp('cleared_at')->nullable();
            $table->timestamp('shelved_until')->nullable(); $table->text('shelve_reason')->nullable();
            $table->boolean('first_out')->default(false); $table->timestamps();
        });
        Schema::create('alarm_events', function (Blueprint $table) {
            $table->id(); $table->string('alarm_uid'); $table->string('event'); $table->longText('payload_json'); $table->timestamps();
        });
        Schema::create('assessments', function (Blueprint $table) {
            $table->id(); $table->string('subject'); $table->integer('risk_score'); $table->string('confidence');
            $table->longText('factors_json'); $table->timestamps();
        });
        Schema::create('notifications', function (Blueprint $table) {
            $table->id(); $table->string('alarm_uid')->nullable(); $table->string('channel'); $table->string('recipient')->nullable();
            $table->string('status')->default('queued'); $table->timestamp('sent_at')->nullable(); $table->text('error')->nullable(); $table->timestamps();
        });
        Schema::create('assets', function (Blueprint $table) {
            $table->id(); $table->string('asset_code')->unique(); $table->string('type'); $table->string('parent')->nullable();
            $table->string('segment_id')->nullable(); $table->date('installed_on')->nullable(); $table->date('last_inspection')->nullable();
            $table->date('next_inspection')->nullable(); $table->float('corrosion_index')->default(0); $table->text('notes')->nullable(); $table->timestamps();
        });
        Schema::create('maintenance_records', function (Blueprint $table) {
            $table->id(); $table->foreignId('asset_id')->constrained()->cascadeOnDelete(); $table->date('performed_on');
            $table->string('performed_by'); $table->text('summary')->nullable(); $table->string('result')->nullable(); $table->timestamps();
        });
        Schema::create('scenario_runs', function (Blueprint $table) {
            $table->id(); $table->string('scenario'); $table->longText('params_json')->nullable(); $table->timestamp('started_at');
            $table->timestamp('ended_at')->nullable(); $table->longText('score_json')->nullable(); $table->foreignId('user_id')->nullable()->constrained(); $table->timestamps();
        });
        Schema::create('audit_log', function (Blueprint $table) {
            $table->id(); $table->foreignId('user_id')->nullable()->constrained(); $table->string('action');
            $table->longText('payload_json')->nullable(); $table->timestamps();
        });
        Schema::create('settings', function (Blueprint $table) {
            $table->string('key')->primary(); $table->longText('value_json'); $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        foreach (['settings','audit_log','scenario_runs','maintenance_records','assets','notifications','assessments','alarm_events','alarms'] as $table) Schema::dropIfExists($table);
        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn(['role','telegram_chat_id']);
        });
    }
};

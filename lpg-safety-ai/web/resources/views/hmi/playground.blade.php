<x-app-layout>
    <x-slot name="header"><h2 class="font-semibold text-xl">Simulation Playground</h2></x-slot>

    <div class="p-6 space-y-6">
        <div class="grid lg:grid-cols-3 gap-4">
            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Environment</h3>
                <label class="block text-sm font-medium">Outside temperature: <span id="ambientValue">30</span> °C</label>
                <input id="ambient" type="range" min="-10" max="60" value="30" class="w-full">

                <label class="block text-sm font-medium mt-4">Solar gain: <span id="solarValue">4</span> °C</label>
                <input id="solar" type="range" min="0" max="8" value="4" class="w-full">
            </section>

            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Tank T01</h3>
                <label class="block text-sm font-medium">Liquid temperature: <span id="tankTempValue">30</span> °C</label>
                <input id="tankTemp" type="range" min="-10" max="100" value="30" class="w-full">

                <label class="block text-sm font-medium mt-4">Gauge pressure: <span id="tankPressureValue">8</span> barg</label>
                <input id="tankPressure" type="range" min="0" max="25" step="0.1" value="8" class="w-full">

                <label class="block text-sm font-medium mt-4">Liquid level: <span id="tankLevelValue">62</span>%</label>
                <input id="tankLevel" type="range" min="0" max="100" value="62" class="w-full">
            </section>

            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Valves & Pump</h3>
                <label class="block text-sm font-medium">Inlet valve: <span id="inletValue">0</span>%</label>
                <input id="inletValve" type="range" min="0" max="100" value="0" class="w-full">

                <label class="block text-sm font-medium mt-4">Outlet valve: <span id="outletValue">0</span>%</label>
                <input id="outletValve" type="range" min="0" max="100" value="0" class="w-full">

                <label class="flex items-center gap-2 mt-4 text-sm font-medium">
                    <input id="pumpOn" type="checkbox" checked> Pipeline pump on
                </label>

                <label class="block text-sm font-medium mt-3">Pump speed: <span id="pumpValue">70</span>%</label>
                <input id="pumpSpeed" type="range" min="0" max="100" value="70" class="w-full">
            </section>
        </div>

        <div class="grid lg:grid-cols-3 gap-4">
            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Manual Leak</h3>
                <label class="block text-sm font-medium">Leak asset</label>
                <select id="leakAsset" class="border w-full mt-1">
                    <option value="XV-T01-OUT">T01 outlet valve</option>
                    <option value="P-T01">T01 pump seal</option>
                    <option value="FLG-S1-01">S1 flange 01</option>
                    <option value="FLG-S2-01">S2 flange 01</option>
                    <option value="FLG-S3-01">S3 flange 01</option>
                    <option value="FLG-S4-01">S4 flange 01</option>
                </select>

                <label class="block text-sm font-medium mt-4">Leak size: <span id="leakValue">0</span> mm²</label>
                <input id="leakArea" type="range" min="0" max="250" value="0" class="w-full">

                <label class="flex items-center gap-2 mt-4 text-sm font-medium">
                    <input id="leakEnabled" type="checkbox"> Enable leak
                </label>
            </section>

            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Presets</h3>
                <select id="scenario" class="border w-full">
                    <option value="normal_day">Normal day</option>
                    <option value="heat_wave">Heat wave</option>
                    <option value="overfill">Overfill</option>
                    <option value="valve_leak">Valve leak</option>
                    <option value="flange_seep">Flange seep</option>
                    <option value="weld_rupture">Weld rupture</option>
                    <option value="pump_seal">Pump seal</option>
                    <option value="maintenance_mode">Maintenance mode</option>
                </select>
                <button id="runPreset" class="mt-3 bg-blue-700 text-white px-4 py-2 rounded w-full">Run preset</button>
                <button id="resetSim" class="mt-2 border border-gray-400 px-4 py-2 rounded w-full">Reset simulation</button>
            </section>

            <section class="bg-white p-4 rounded shadow">
                <h3 class="font-bold text-lg mb-4">Live Readings</h3>
                <div id="liveReadings" class="space-y-2 text-sm">Waiting for simulator…</div>
                <div id="statusMessage" class="mt-3 text-xs text-gray-500">Manual controls apply immediately.</div>
            </section>
        </div>
    </div>

    <script>
        const qs = id => document.getElementById(id);

        async function postJson(url, body) {
            const response = await fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRF-TOKEN': '{{ csrf_token() }}'},
                body: JSON.stringify(body)
            });
            if (!response.ok) throw new Error(await response.text());
            return response.json();
        }

        async function applyManualControls() {
            qs('statusMessage').textContent = 'Applying controls…';
            const leakArea = qs('leakEnabled').checked ? Number(qs('leakArea').value) : 0;
            try {
                await postJson('/api/playground/control', {
                    ambient_c: Number(qs('ambient').value),
                    solar_gain_c: Number(qs('solar').value),
                    tanks: {T01: {
                        temperature_override_c: Number(qs('tankTemp').value),
                        pressure_override_barg: Number(qs('tankPressure').value),
                        level_override_pct: Number(qs('tankLevel').value),
                        fill_valve_pct: Number(qs('inletValve').value),
                        outlet_valve_pct: Number(qs('outletValve').value)
                    }},
                    pipeline: {
                        pump_on: qs('pumpOn').checked,
                        pump_speed: Number(qs('pumpSpeed').value)
                    },
                    leaks: [{asset: qs('leakAsset').value, area_mm2: leakArea, mode: leakArea > 0 ? 'leaking' : 'healthy'}]
                });
                qs('statusMessage').textContent = 'Manual controls applied.';
            } catch (error) {
                qs('statusMessage').textContent = 'Control rejected: ' + error.message;
            }
        }

        function bindRange(id, valueId, suffix = '') {
            const input = qs(id);
            input.addEventListener('input', () => qs(valueId).textContent = input.value + suffix);
            input.addEventListener('change', applyManualControls);
        }

        bindRange('ambient', 'ambientValue', '');
        bindRange('solar', 'solarValue', '');
        bindRange('tankTemp', 'tankTempValue', '');
        bindRange('tankPressure', 'tankPressureValue', '');
        bindRange('tankLevel', 'tankLevelValue', '');
        bindRange('inletValve', 'inletValue', '');
        bindRange('outletValve', 'outletValue', '');
        bindRange('pumpSpeed', 'pumpValue', '');
        bindRange('leakArea', 'leakValue', '');

        qs('pumpOn').addEventListener('change', applyManualControls);
        qs('leakEnabled').addEventListener('change', applyManualControls);
        qs('leakAsset').addEventListener('change', applyManualControls);

        qs('runPreset').addEventListener('click', async () => {
            qs('statusMessage').textContent = 'Running preset…';
            await postJson('/api/playground/scenario/' + qs('scenario').value, {});
            qs('statusMessage').textContent = 'Preset started.';
        });

        qs('resetSim').addEventListener('click', async () => {
            await postJson('/api/playground/reset', {seed: 42});
            qs('statusMessage').textContent = 'Simulation reset.';
        });

        async function refreshLive() {
            try {
                const response = await fetch('/api/live');
                const data = await response.json();
                const tags = data.frame?.tags || {};
                qs('liveReadings').innerHTML = `
                    <div>Outside: <b>${tags['AT-AMB']?.value ?? '--'} °C</b></div>
                    <div>Tank level: <b>${tags['LT-T01']?.value ?? '--'}%</b></div>
                    <div>Tank pressure: <b>${tags['PT-T01']?.value ?? '--'} barg</b></div>
                    <div>Tank temperature: <b>${tags['TT-T01A']?.value ?? '--'} °C</b></div>
                    <div>Pump: <b>${document.getElementById('pumpOn').checked ? 'ON' : 'OFF'}</b></div>
                `;
            } catch (_) {
                qs('liveReadings').textContent = 'Simulator offline';
            }
        }

        setInterval(refreshLive, 1000);
        refreshLive();
    </script>
</x-app-layout>

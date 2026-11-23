<x-app-layout>
<x-slot name="header"><h2 class="font-semibold text-xl text-gray-800">LPG Safety Overview</h2></x-slot>
<div class="py-6" x-data="hmi()"><div class="max-w-7xl mx-auto px-4">
<div x-show="offline" class="mb-4 rounded bg-red-700 text-white p-3">AI advisory offline — stale values are not accepted as live</div>
<div class="grid md:grid-cols-3 gap-4">
<template x-for="tank in ['T01','T02','T03']"><div class="bg-white rounded shadow p-4">
<h3 class="font-bold" x-text="tank"></h3><div class="mt-2 text-sm" x-text="summary(tank)"></div>
<a :href="'/tanks/'+tank" class="text-blue-700 text-sm">Open tank detail</a></div></template>
</div>
<div class="mt-6 bg-white rounded shadow p-4"><h3 class="font-bold">Pipeline</h3><div class="grid grid-cols-4 gap-2 mt-3"><template x-for="i in 4"><div class="h-12 rounded bg-sky-600 text-white flex items-center justify-center">S<i></i></div></template></div></div>
</div></div>
<script>function hmi(){return{offline:false,data:{},init(){this.poll()},summary(t){let x=this.data.tank_summary?.[t];return x?`Level ${x.level_pct?.toFixed(1)}% · Pressure ${x.P_gauge?.toFixed(2)} barg · Temp ${x.T_liquid?.toFixed(1)} °C`:'Waiting for AI service'},async poll(){try{let r=await fetch('/api/live');if(!r.ok)throw 0;this.data=await r.json();this.offline=!!this.data.offline}catch(e){this.offline=true}setTimeout(()=>this.poll(),1000)}}}</script>
</x-app-layout>

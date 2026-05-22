import os
import json
import socket
import webbrowser
import threading
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

from eval_factory.config import config
from eval_factory.serialization import RobustEncoder

# The highly premium Single Page Application (SPA) HTML template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>eval-factory Dashboard</title>
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        outfit: ['Outfit', 'sans-serif'],
                        mono: ['Fira Code', 'monospace']
                    }
                }
            }
        }
    </script>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
    <!-- FontAwesome for Premium Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Alpine.js CDN -->
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #090d16;
            color: #e2e8f0;
        }
        .custom-scrollbar::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
            background: #0b0f19;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #1e293b;
            border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #334155;
        }
        .glass-card {
            background: rgba(19, 27, 46, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(31, 46, 77, 0.5);
        }
        .glow-accent {
            box-shadow: 0 0 25px rgba(59, 130, 246, 0.15);
        }
        .glow-green {
            box-shadow: 0 0 25px rgba(16, 185, 129, 0.1);
        }
    </style>
</head>
<body class="min-h-screen custom-scrollbar" x-data="dashboard">
    <!-- App Wrapper -->
    <div class="flex flex-col h-screen overflow-hidden">
        
        <!-- Header -->
        <header class="border-b border-[#1f2e4d] bg-[#0b0f19]/90 px-8 py-4 flex items-center justify-between z-10">
            <div class="flex items-center space-x-3">
                <div class="bg-gradient-to-tr from-blue-600 to-indigo-500 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-flask text-white text-xl"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold font-outfit bg-gradient-to-r from-blue-400 via-indigo-200 to-white bg-clip-text text-transparent">
                        eval-factory
                    </h1>
                    <p class="text-xs text-slate-400">Interactive Evaluation Suite</p>
                </div>
            </div>
            
            <div class="flex items-center space-x-4">
                <span class="text-xs text-slate-500">Dataset File:</span>
                <div class="px-3 py-1.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 font-mono text-xs flex items-center space-x-2">
                    <i class="fa-solid fa-file-invoice-dollar"></i>
                    <span>{{DATASET_NAME}}.jsonl</span>
                </div>
                <button @click="fetchRuns()" class="text-slate-400 hover:text-white transition p-2 rounded-lg bg-[#131b2e] border border-[#1f2e4d]">
                    <i class="fa-solid fa-rotate"></i>
                </button>
            </div>
        </header>

        <!-- KPI Metrics & Grid Dashboard -->
        <div class="flex-1 flex overflow-hidden">
            
            <!-- Main Content Area -->
            <div class="flex-1 flex flex-col overflow-hidden px-8 py-6 space-y-6">
                
                <!-- KPI Dashboard Counters -->
                <div class="grid grid-cols-4 gap-6">
                    <div class="glass-card rounded-2xl p-5 flex items-center space-x-4">
                        <div class="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 text-xl">
                            <i class="fa-solid fa-database"></i>
                        </div>
                        <div>
                            <p class="text-xs text-slate-400 uppercase font-semibold tracking-wider font-outfit">Captured Runs</p>
                            <h3 class="text-2xl font-bold font-outfit text-white mt-0.5" x-text="totalRuns">0</h3>
                        </div>
                    </div>
                    
                    <div class="glass-card rounded-2xl p-5 flex items-center space-x-4">
                        <div class="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-xl">
                            <i class="fa-solid fa-clock"></i>
                        </div>
                        <div>
                            <p class="text-xs text-slate-400 uppercase font-semibold tracking-wider font-outfit">Avg Latency</p>
                            <h3 class="text-2xl font-bold font-outfit text-white mt-0.5" x-text="avgDuration + 's'">0s</h3>
                        </div>
                    </div>
                    
                    <div class="glass-card rounded-2xl p-5 flex items-center space-x-4">
                        <div class="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 text-xl">
                            <i class="fa-solid fa-receipt"></i>
                        </div>
                        <div>
                            <p class="text-xs text-slate-400 uppercase font-semibold tracking-wider font-outfit">Estimated Cost</p>
                            <h3 class="text-2xl font-bold font-outfit text-white mt-0.5" x-text="'$' + totalCost">$0.0000</h3>
                        </div>
                    </div>
                    
                    <div class="glass-card rounded-2xl p-5 flex items-center space-x-4" :class="accuracy !== 'N/A' && 'glow-green'">
                        <div class="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 text-xl">
                            <i class="fa-solid fa-square-poll-vertical"></i>
                        </div>
                        <div>
                            <p class="text-xs text-slate-400 uppercase font-semibold tracking-wider font-outfit">Correctness Rate</p>
                            <h3 class="text-2xl font-bold font-outfit text-white mt-0.5" x-text="accuracy">N/A</h3>
                        </div>
                    </div>
                </div>

                <!-- Main Layout splits List and Inspector -->
                <div class="flex-1 flex overflow-hidden gap-6">
                    
                    <!-- LEFT COLUMN: Runs List -->
                    <div class="w-1/3 flex flex-col glass-card rounded-2xl overflow-hidden border border-[#1f2e4d]">
                        <!-- Search and Filter -->
                        <div class="p-4 border-b border-[#1f2e4d] bg-[#0b0f19]/40 space-y-3">
                            <div class="relative">
                                <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-400 text-sm"></i>
                                <input type="text" x-model="searchQuery" placeholder="Search inputs & outputs..." 
                                       class="w-full bg-[#090d16] border border-[#1f2e4d] rounded-xl pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 transition">
                            </div>
                            
                            <!-- Filter Tabs -->
                            <div class="flex space-x-1 bg-[#090d16] p-1 rounded-lg border border-[#1f2e4d]">
                                <button @click="statusFilter = 'all'" :class="statusFilter === 'all' && 'bg-[#1e293b] text-white'" class="flex-1 py-1 text-xs rounded font-medium text-slate-400 hover:text-white transition">All</button>
                                <button @click="statusFilter = 'correct'" :class="statusFilter === 'correct' && 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/30'" class="flex-1 py-1 text-xs rounded font-medium text-slate-400 hover:text-white transition">Correct</button>
                                <button @click="statusFilter = 'incorrect'" :class="statusFilter === 'incorrect' && 'bg-rose-950/80 text-rose-400 border border-rose-500/30'" class="flex-1 py-1 text-xs rounded font-medium text-slate-400 hover:text-white transition">Incorrect</button>
                                <button @click="statusFilter = 'pending'" :class="statusFilter === 'pending' && 'bg-[#1e293b] text-white'" class="flex-1 py-1 text-xs rounded font-medium text-slate-400 hover:text-white transition">Pending</button>
                            </div>
                        </div>

                        <!-- Scrollable Cards -->
                        <div class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2 bg-[#0b0f19]/20">
                            <!-- Loading / Empty States -->
                            <template x-if="loading">
                                <div class="text-center py-12 text-slate-400 space-y-2">
                                    <i class="fa-solid fa-circle-notch fa-spin text-2xl text-blue-500"></i>
                                    <p class="text-xs">Loading dataset records...</p>
                                </div>
                            </template>
                            <template x-if="!loading && filteredRuns.length === 0">
                                <div class="text-center py-12 text-slate-500 space-y-2">
                                    <i class="fa-solid fa-inbox text-3xl"></i>
                                    <p class="text-xs">No matching runs found.</p>
                                </div>
                            </template>

                            <!-- Run Cards -->
                            <template x-for="run in filteredRuns" :key="run.run_id">
                                <div @click="selectRun(run)" 
                                     :class="selectedRun && selectedRun.run_id === run.run_id ? 'border-blue-500 bg-blue-950/20' : 'border-[#1f2e4d] hover:border-slate-600 bg-[#131b2e]/40'"
                                     class="p-4 rounded-xl border transition cursor-pointer text-left relative flex flex-col space-y-2">
                                    
                                    <div class="flex justify-between items-start">
                                        <!-- Correctness Badge -->
                                        <template x-if="getRunStatus(run).type === 'correct'">
                                            <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                                                <i class="fa-solid fa-circle-check mr-1"></i> Correct
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'incorrect'">
                                            <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-rose-950 text-rose-400 border border-rose-500/30">
                                                <i class="fa-solid fa-circle-xmark mr-1"></i> <span x-text="getRunStatus(run).label"></span>
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'partial'">
                                            <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-amber-950/80 text-amber-400 border border-amber-500/30 font-medium">
                                                <i class="fa-solid fa-circle-notch mr-1"></i> <span x-text="getRunStatus(run).label"></span>
                                            </span>
                                        </template>
                                        <template x-if="getRunStatus(run).type === 'pending'">
                                            <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-[#1e293b] text-slate-300">
                                                <i class="fa-solid fa-circle-question mr-1"></i> Pending
                                            </span>
                                        </template>

                                        <!-- Timestamp -->
                                        <span class="text-[10px] text-slate-500" x-text="formatTime(run.timestamp)">Just now</span>
                                    </div>

                                    <!-- input preview -->
                                    <p class="text-sm font-medium text-slate-200 line-clamp-2" x-text="getSidebarPreview(run)"></p>
                                    
                                    <!-- mini stats -->
                                    <div class="flex items-center space-x-3 text-[10px] text-slate-400 font-mono">
                                        <span><i class="fa-solid fa-hourglass-half mr-1 text-slate-500"></i> <span x-text="parseFloat(run.metadata?.duration_seconds || 0).toFixed(2) + 's'"></span></span>
                                        <template x-if="run.metadata?.tokens">
                                            <span><i class="fa-solid fa-coins mr-1 text-slate-500"></i> <span x-text="run.metadata.tokens.total_tokens + ' t'"></span></span>
                                        </template>
                                    </div>
                                </div>
                            </template>
                        </div>
                    </div>

                    <!-- RIGHT COLUMN: Run Inspector -->
                    <div class="w-2/3 flex flex-col glass-card rounded-2xl overflow-hidden border border-[#1f2e4d] bg-[#131b2e]/20">
                        <template x-if="!selectedRun">
                            <div class="flex-1 flex flex-col items-center justify-center text-slate-500 space-y-3">
                                <i class="fa-solid fa-flask-vial text-5xl bg-gradient-to-tr from-blue-500/10 to-indigo-500/10 p-6 rounded-3xl border border-indigo-500/10"></i>
                                <p class="text-sm">Select a captured run from the list to inspect it.</p>
                            </div>
                        </template>
                        
                        <template x-if="selectedRun">
                            <div class="flex-grow flex flex-col overflow-hidden">
                                <!-- Inspector Header -->
                                <div class="p-6 border-b border-[#1f2e4d] bg-[#0b0f19]/40 flex items-center justify-between">
                                    <div>
                                        <div class="flex items-center space-x-2">
                                            <h2 class="text-lg font-bold font-outfit text-white">Run Inspector</h2>
                                            <span class="text-xs font-mono text-slate-500 bg-[#090d16] px-2 py-0.5 rounded border border-[#1f2e4d]" x-text="selectedRun?.run_id ? selectedRun.run_id.substring(0, 8) + '...' : ''"></span>
                                        </div>
                                        <p class="text-xs text-slate-400 mt-1" x-text="selectedRun ? 'Executed on: ' + new Date(selectedRun.timestamp).toLocaleString() : ''">Just now</p>
                                    </div>

                                    <!-- Top Right Mini Badges -->
                                    <div class="flex space-x-3 text-xs font-mono bg-[#090d16] px-4 py-2 rounded-xl border border-[#1f2e4d]">
                                        <div>
                                            <span class="text-slate-500">Latency:</span>
                                            <span class="text-blue-400 font-semibold" x-text="parseFloat(selectedRun?.metadata?.duration_seconds || 0).toFixed(3) + 's'"></span>
                                        </div>
                                        <div class="border-l border-slate-700 h-4 my-auto mx-2"></div>
                                        <template x-if="selectedRun?.metadata?.tokens">
                                            <div class="flex space-x-3">
                                                <div>
                                                    <span class="text-slate-500">Tokens:</span>
                                                    <span class="text-purple-400 font-semibold" x-text="selectedRun?.metadata?.tokens?.total_tokens || 0"></span>
                                                </div>
                                                <div class="border-l border-slate-700 h-4 my-auto mx-2"></div>
                                                <div>
                                                    <span class="text-slate-500">Cost:</span>
                                                    <span class="text-emerald-400 font-semibold" x-text="selectedRun?.metadata?.tokens?.total_cost ? '$' + selectedRun.metadata.tokens.total_cost.toFixed(4) : '$0.0000'"></span>
                                                </div>
                                            </div>
                                        </template>
                                    </div>
                                </div>

                                <!-- Inspector Scrollable Body -->
                                <div class="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6 bg-[#0b0f19]/10">
                                    
                                    <!-- 1. System Prompt (collapsible) -->
                                    <template x-if="selectedRun?.metadata?.system_prompts && selectedRun.metadata.system_prompts.length > 0">
                                        <div x-data="{ open: false }" class="rounded-xl border border-indigo-500/20 bg-indigo-950/20 p-4 space-y-2">
                                            <button @click="open = !open" class="w-full flex items-center justify-between text-xs font-bold text-indigo-400 uppercase tracking-wider font-outfit focus:outline-none">
                                                <div class="flex items-center space-x-2">
                                                    <i class="fa-solid fa-robot animate-pulse"></i>
                                                    <span>System Prompt (<span x-text="selectedRun?.metadata?.system_prompts?.length || 0"></span> captured)</span>
                                                </div>
                                                <i class="fa-solid text-indigo-300 transition-transform duration-200" :class="open ? 'fa-chevron-up rotate-180' : 'fa-chevron-down'"></i>
                                            </button>
                                            <div x-show="open" x-transition class="mt-2 text-sm text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-[#090d16]/60 p-3.5 rounded-lg border border-indigo-950/60" x-text="selectedRun?.metadata?.system_prompts ? selectedRun.metadata.system_prompts.join('\\n\\n') : ''"></div>
                                        </div>
                                    </template>

                                    <!-- 2. Pair Cards Iterator -->
                                    <template x-for="(ev, index) in (selectedRun?.evaluation || [])" :key="index">
                                        <div x-data="{ showMetadata: false }" class="glass-card rounded-2xl p-6 border-[#1f2e4d] bg-[#131b2e]/30 space-y-4 shadow-xl">
                                            
                                            <!-- Pair Header -->
                                            <div class="flex items-center justify-between border-b border-[#1f2e4d]/80 pb-3">
                                                <div class="flex items-center space-x-2">
                                                    <span class="w-6 h-6 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-xs font-bold text-blue-400" x-text="index + 1"></span>
                                                    <h3 class="text-sm font-bold font-outfit text-white">Evaluation Pair #<span x-text="index + 1"></span></h3>
                                                </div>
                                                
                                                <!-- Mini Status for Pair -->
                                                <div>
                                                    <template x-if="ev.correct === true">
                                                        <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-emerald-950 text-emerald-400 border border-emerald-500/30">
                                                            <i class="fa-solid fa-circle-check mr-1"></i> Correct
                                                        </span>
                                                    </template>
                                                    <template x-if="ev.correct === false">
                                                        <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-rose-950 text-rose-400 border border-rose-500/30">
                                                            <i class="fa-solid fa-circle-xmark mr-1"></i> Incorrect
                                                        </span>
                                                    </template>
                                                    <template x-if="ev.correct === null || ev.correct === undefined">
                                                        <span class="px-2 py-0.5 text-[10px] font-semibold rounded bg-[#1e293b] text-slate-400 border border-[#1f2e4d]">
                                                            <i class="fa-solid fa-circle-question mr-1"></i> Pending Review
                                                        </span>
                                                    </template>
                                                </div>
                                            </div>

                                            <!-- Clean Input Prompt Preview -->
                                            <div class="space-y-1.5 text-left">
                                                <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Input Prompt</span>
                                                <div class="bg-[#0b0f19]/60 border border-[#1f2e4d]/60 rounded-xl p-3.5 text-sm text-slate-300 leading-relaxed font-medium whitespace-pre-wrap select-all"
                                                     x-text="getCleanText(isBatchRun(selectedRun) ? selectedRun.inputs[index] : selectedRun.inputs)">
                                                </div>
                                            </div>

                                            <!-- Clean Model Response (Big Content Box) -->
                                            <div class="space-y-1.5 text-left">
                                                <span class="text-[10px] font-bold text-blue-400 uppercase tracking-wider font-outfit flex items-center space-x-1.5">
                                                    <i class="fa-solid fa-magic-wand-sparkles"></i>
                                                    <span>Model Response</span>
                                                </span>
                                                <div class="bg-gradient-to-br from-[#1e293b]/40 to-[#0f172a]/70 border border-blue-500/25 text-slate-100 text-base font-outfit font-medium leading-relaxed p-5 rounded-2xl shadow-inner whitespace-pre-wrap select-all"
                                                     x-text="getCleanText(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)">
                                                </div>
                                            </div>

                                            <!-- Evaluator Playground (Always visible under big content) -->
                                            <div class="grid grid-cols-3 gap-4 items-end pt-3 border-t border-[#1f2e4d]/40">
                                                <div class="col-span-2 space-y-1.5 text-left">
                                                    <label class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Expected Ground Truth Response (Optional)</label>
                                                    <input type="text" x-model="ev.ground_truth" placeholder="Define expected output..." 
                                                           class="w-full bg-[#090d16] border border-[#1f2e4d] rounded-xl px-3 py-2 text-xs text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 transition">
                                                </div>

                                                <div class="space-y-1.5 flex flex-col justify-end text-left">
                                                    <label class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Correctness</label>
                                                    <div class="flex space-x-1">
                                                        <button @click="ev.correct = true" 
                                                                :class="ev.correct === true ? 'bg-emerald-950 text-emerald-400 border-emerald-500/80 glow-green' : 'bg-transparent text-slate-500 border-[#1f2e4d] hover:border-slate-600'" 
                                                                class="flex-1 py-1.5 border rounded-lg font-bold text-[10px] flex items-center justify-center space-x-1 transition duration-150">
                                                            <i class="fa-solid fa-check"></i>
                                                            <span>Yes</span>
                                                        </button>
                                                        <button @click="ev.correct = false" 
                                                                :class="ev.correct === false ? 'bg-rose-950 text-rose-400 border-rose-500/80' : 'bg-transparent text-slate-500 border-[#1f2e4d] hover:border-slate-600'" 
                                                                class="flex-1 py-1.5 border rounded-lg font-bold text-[10px] flex items-center justify-center space-x-1 transition duration-150">
                                                            <i class="fa-solid fa-xmark"></i>
                                                            <span>No</span>
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>

                                            <!-- Actions Bar (Save & Toggle Metadata) -->
                                            <div class="flex items-center justify-between pt-2 border-t border-[#1f2e4d]/20">
                                                <!-- Left: Toggle Metadata Link -->
                                                <button @click="showMetadata = !showMetadata" 
                                                        class="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1.5 transition">
                                                    <i class="fa-solid" :class="showMetadata ? 'fa-eye-slash' : 'fa-code'"></i>
                                                    <span x-text="showMetadata ? 'Hide Response Metadata & Raw Payload' : 'Show Response Metadata & Raw Payload'"></span>
                                                </button>

                                                <!-- Right: Save Pair button -->
                                                <button @click="saveReview(index, ev.correct, ev.ground_truth)" 
                                                        :disabled="savingReviewIndex === index"
                                                        class="px-4 py-2 rounded-xl font-bold text-xs bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white shadow-md shadow-blue-500/10 active:scale-[0.98] transition flex items-center space-x-1.5 disabled:opacity-50">
                                                    <template x-if="savingReviewIndex === index">
                                                        <i class="fa-solid fa-circle-notch fa-spin"></i>
                                                    </template>
                                                    <template x-if="savingReviewIndex !== index">
                                                        <i class="fa-solid fa-floppy-disk"></i>
                                                    </template>
                                                    <span x-text="savingReviewIndex === index ? 'Saving...' : 'Save Pair Evaluation'"></span>
                                                </button>
                                            </div>

                                            <!-- Collapsible Raw Payload & Metadata -->
                                            <div x-show="showMetadata" x-transition class="space-y-4 pt-4 border-t border-[#1f2e4d]/40">
                                                <!-- Structured Metadata Grid -->
                                                <template x-if="getPairMetadata(selectedRun, index)">
                                                    <div class="grid grid-cols-3 gap-4 bg-[#090d16]/50 p-4 rounded-xl border border-[#1f2e4d]/60">
                                                        <template x-if="getPairMetadata(selectedRun, index)?.model">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-wider font-mono">Model Name</span>
                                                                <p class="text-xs font-mono text-blue-300 font-semibold" x-text="getPairMetadata(selectedRun, index)?.model"></p>
                                                            </div>
                                                        </template>
                                                        <template x-if="getPairMetadata(selectedRun, index)?.tokens">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-wider font-mono">Tokens Generated</span>
                                                                <p class="text-xs font-mono text-purple-300 font-semibold">
                                                                    <span class="font-bold" x-text="getPairMetadata(selectedRun, index)?.tokens?.total || 0"></span> total
                                                                    <span class="text-slate-500 text-[10px]" x-text="getPairMetadata(selectedRun, index)?.tokens ? '(' + getPairMetadata(selectedRun, index).tokens.prompt + ' prompt, ' + getPairMetadata(selectedRun, index).tokens.completion + ' completion)' : ''"></span>
                                                                </p>
                                                            </div>
                                                        </template>
                                                        <template x-if="getPairMetadata(selectedRun, index)?.finish_reason">
                                                            <div class="space-y-1 text-left">
                                                                <span class="text-[9px] font-bold text-slate-500 uppercase tracking-wider font-mono">Finish Reason</span>
                                                                <p class="text-xs font-mono text-emerald-300 font-semibold flex items-center space-x-1.5">
                                                                    <span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                                                    <span x-text="getPairMetadata(selectedRun, index)?.finish_reason"></span>
                                                                </p>
                                                            </div>
                                                        </template>
                                                    </div>
                                                </template>

                                                <div class="grid grid-cols-2 gap-4">
                                                    <div class="space-y-1.5 text-left">
                                                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Raw Input JSON</label>
                                                        <pre class="h-48 overflow-y-auto custom-scrollbar bg-[#090d16] border border-[#1f2e4d] rounded-xl p-3 font-mono text-[11px] text-slate-400 whitespace-pre-wrap text-left select-all" 
                                                             x-text="formatPrettyJSON(isBatchRun(selectedRun) ? selectedRun.inputs[index] : selectedRun.inputs)"></pre>
                                                    </div>
                                                    <div class="space-y-1.5 text-left">
                                                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Raw Output JSON</label>
                                                        <pre class="h-48 overflow-y-auto custom-scrollbar bg-[#090d16] border border-[#1f2e4d] rounded-xl p-3 font-mono text-[11px] text-slate-400 whitespace-pre-wrap text-left select-all" 
                                                             x-text="formatPrettyJSON(isBatchRun(selectedRun) ? selectedRun.outputs[index] : selectedRun.outputs)"></pre>
                                                    </div>
                                                </div>
                                            </div>

                                        </div>
                                    </template>
                                </div>
                            </div>
                        </template>
                    </div>

                </div>
            </div>
            
        </div>
    </div>

    <!-- Scripting for State Machine -->
    <script>
        document.addEventListener('alpine:init', () => {
            Alpine.data('dashboard', () => ({
                runs: [],
                loading: true,
                errorMsg: '',
                searchQuery: '',
                statusFilter: 'all',
                selectedRun: null,
                savingReviewIndex: null,

                init() {
                    this.fetchRuns();
                },

                async fetchRuns() {
                    this.loading = true;
                    try {
                        const res = await fetch('/api/runs');
                        if (!res.ok) throw new Error('Failed to load runs');
                        const rawRuns = await res.json();
                        
                        // Normalize evaluations on-the-fly for clean pair-wise binding
                        this.runs = rawRuns.map(run => {
                            const inputs = run.inputs;
                            const outputs = run.outputs;
                            const isBatch = Array.isArray(inputs) && Array.isArray(outputs) && inputs.length === outputs.length;
                            const numItems = isBatch ? inputs.length : 1;
                            
                            let evals = run.evaluation;
                            if (!Array.isArray(evals)) {
                                evals = [evals || {}];
                            }
                            
                            const normalizedEvals = [];
                            for (let i = 0; i < numItems; i++) {
                                normalizedEvals.push({
                                    correct: evals[i] ? evals[i].correct : null,
                                    ground_truth: (evals[i] && evals[i].ground_truth) ? evals[i].ground_truth : ''
                                });
                            }
                            
                            run.evaluation = normalizedEvals;
                            return run;
                        });
                        
                        // Pick first run by default if none selected or not found
                        if (this.runs.length > 0) {
                            const found = this.selectedRun ? this.runs.find(r => r.run_id === this.selectedRun.run_id) : null;
                            this.selectRun(found || this.runs[0]);
                        } else {
                            this.selectedRun = null;
                        }
                    } catch (err) {
                        this.errorMsg = err.message;
                    } finally {
                        this.loading = false;
                    }
                },

                selectRun(run) {
                    this.selectedRun = run;
                },

                async saveReview(index, correct, groundTruth) {
                    if (!this.selectedRun) return;
                    this.savingReviewIndex = index;
                    try {
                        const res = await fetch('/api/review', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            run_id: this.selectedRun.run_id,
                            item_index: index,
                            correct: correct,
                            ground_truth: groundTruth
                          })
                        });
                        if (!res.ok) throw new Error('Failed to save review');
                        
                        // Alpine.js model is already updated via reactive binding!
                    } catch (err) {
                        alert("Error saving review: " + err.message);
                    } finally {
                        this.savingReviewIndex = null;
                    }
                },

                // Helper to summarize inputs cleanly for the sidebar list
                getSidebarPreview(run) {
                    if (!run) return '';
                    const inputs = run.inputs;
                    if (Array.isArray(inputs)) {
                        const previews = inputs.map(inp => {
                            if (inp && typeof inp === 'object') {
                                const vals = Object.values(inp).filter(v => typeof v !== 'object' && v !== null);
                                if (vals.length > 0) return vals.join(', ');
                                return JSON.stringify(inp);
                            }
                            return String(inp);
                        });
                        return `Batch (${inputs.length}): ` + previews.join(' | ');
                    } else if (inputs && typeof inputs === 'object') {
                        const vals = Object.values(inputs).filter(v => typeof v !== 'object' && v !== null);
                        if (vals.length > 0) return vals.join(', ');
                        return JSON.stringify(inputs);
                    }
                    return String(inputs);
                },

                // Helper to extract granular pair-wise metadata (Model Name, Tokens, Finish Reason)
                getPairMetadata(run, index) {
                    if (!run) return null;
                    const output = this.isBatchRun(run) ? run.outputs[index] : run.outputs;
                    if (!output || typeof output !== 'object') return null;

                    const metadata = {};
                    
                    // Model
                    if (output.response_metadata && output.response_metadata.model_name) {
                        metadata.model = output.response_metadata.model_name;
                    } else if (output.response_metadata && output.response_metadata.model) {
                        metadata.model = output.response_metadata.model;
                    }
                    
                    // Provider
                    if (output.response_metadata && output.response_metadata.model_provider) {
                        metadata.provider = output.response_metadata.model_provider;
                    }

                    // Finish Reason
                    if (output.response_metadata && output.response_metadata.finish_reason) {
                        metadata.finish_reason = output.response_metadata.finish_reason;
                    }

                    // Token usage
                    let tokens = null;
                    if (output.usage_metadata) {
                        tokens = {
                            total: output.usage_metadata.total_tokens,
                            prompt: output.usage_metadata.input_tokens,
                            completion: output.usage_metadata.output_tokens
                        };
                    } else if (output.response_metadata && output.response_metadata.token_usage) {
                        const tu = output.response_metadata.token_usage;
                        tokens = {
                            total: tu.total_tokens,
                            prompt: tu.prompt_tokens,
                            completion: tu.completion_tokens
                        };
                    }
                    if (tokens) {
                        metadata.tokens = tokens;
                    }

                    if (Object.keys(metadata).length === 0) return null;
                    return metadata;
                },

                // Helper to check if a run is a batch execution
                isBatchRun(run) {
                    if (!run) return false;
                    return Array.isArray(run.inputs) && Array.isArray(run.outputs) && run.inputs.length === run.outputs.length;
                },

                // Stringifiers & Formatting
                getCleanText(val) {
                    if (!val) return '';
                    if (typeof val === 'string') {
                        try {
                            const parsed = JSON.parse(val);
                            return this.getCleanText(parsed);
                        } catch (e) {
                            return val;
                        }
                    }
                    if (typeof val === 'object') {
                        // Check if it is a LangChain message or message list
                        if (Array.isArray(val)) {
                            return val.map(v => this.getCleanText(v)).join('\\n');
                        }
                        // LangChain constructor format
                        if (val.type === 'constructor' && val.kwargs && val.kwargs.content !== undefined) {
                            return this.getCleanText(val.kwargs.content);
                        }
                        // LangChain standard message format
                        if (val.content !== undefined) {
                            return this.getCleanText(val.content);
                        }
                        if (val.kwargs && val.kwargs.content !== undefined) {
                            return this.getCleanText(val.kwargs.content);
                        }
                        // Simple dictionary (e.g. prompt variables)
                        const keys = Object.keys(val);
                        if (keys.length > 0) {
                            const isSimple = keys.every(k => typeof val[k] !== 'object');
                            if (isSimple) {
                                return keys.map(k => `${k}: ${val[k]}`).join('\\n');
                            }
                        }
                        return JSON.stringify(val, null, 2);
                    }
                    return String(val);
                },

                stringifyPayload(val) {
                    if (typeof val === 'string') return val;
                    if (typeof val === 'object') {
                        if (Array.isArray(val) && val.length > 0) {
                            const item = val[0];
                            if (typeof item === 'object') {
                                return JSON.stringify(val);
                            }
                        }
                        return JSON.stringify(val);
                    }
                    return String(val);
                },

                formatPrettyJSON(val) {
                    if (typeof val === 'string') {
                        try {
                            const parsed = JSON.parse(val);
                            return JSON.stringify(parsed, null, 2);
                        } catch (e) {
                            return val;
                        }
                    }
                    return JSON.stringify(val, null, 2);
                },

                formatTime(timestamp) {
                    try {
                        const date = new Date(timestamp);
                        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                    } catch (e) {
                        return '';
                    }
                },

                // Metric Getters
                get totalRuns() { return this.runs.length; },

                get avgDuration() {
                    if (!this.runs.length) return 0;
                    const sum = this.runs.reduce((acc, r) => acc + (r.metadata?.duration_seconds || 0), 0);
                    return (sum / this.runs.length).toFixed(2);
                },

                get totalCost() {
                    const sum = this.runs.reduce((acc, r) => acc + (r.metadata?.tokens?.total_cost || 0), 0);
                    return sum.toFixed(4);
                },

                get accuracy() {
                    let totalReviewedPairs = 0;
                    let correctPairs = 0;
                    
                    this.runs.forEach(run => {
                        if (Array.isArray(run.evaluation)) {
                            run.evaluation.forEach(ev => {
                                if (ev.correct !== null && ev.correct !== undefined) {
                                    totalReviewedPairs++;
                                    if (ev.correct === true) {
                                        correctPairs++;
                                    }
                                }
                            });
                        }
                    });
                    
                    if (totalReviewedPairs === 0) return 'N/A';
                    return ((correctPairs / totalReviewedPairs) * 100).toFixed(0) + '%';
                },

                // Get run status badge components
                getRunStatus(run) {
                    if (!run || !Array.isArray(run.evaluation)) return { type: 'pending', label: 'Pending' };
                    const total = run.evaluation.length;
                    const correct = run.evaluation.filter(ev => ev.correct === true).length;
                    const incorrect = run.evaluation.filter(ev => ev.correct === false).length;
                    
                    if (incorrect > 0) return { type: 'incorrect', label: `${incorrect}/${total} Incorrect` };
                    if (correct === total) return { type: 'correct', label: 'Correct' };
                    if (correct > 0) return { type: 'partial', label: `${correct}/${total} Correct` };
                    return { type: 'pending', label: 'Pending' };
                },

                // Filter logic
                get filteredRuns() {
                    return this.runs.filter(run => {
                        const inputStr = typeof run.inputs === 'object' ? JSON.stringify(run.inputs) : String(run.inputs);
                        const outputStr = typeof run.outputs === 'object' ? JSON.stringify(run.outputs) : String(run.outputs);
                        const matchSearch = inputStr.toLowerCase().includes(this.searchQuery.toLowerCase()) || 
                                             outputStr.toLowerCase().includes(this.searchQuery.toLowerCase());
                        
                        let matchStatus = true;
                        const status = this.getRunStatus(run).type;
                        if (this.statusFilter === 'correct') {
                            matchStatus = status === 'correct';
                        } else if (this.statusFilter === 'incorrect') {
                            matchStatus = status === 'incorrect';
                        } else if (this.statusFilter === 'pending') {
                            matchStatus = status === 'pending' || status === 'partial';
                        }
                        
                        return matchSearch && matchStatus;
                    });
                }
            }));
        });
    </script>
</body>
</html>
"""


class VisualizerHTTPHandler(BaseHTTPRequestHandler):
    """Custom HTTP server handler to serve the SPA and API endpoints."""

    def log_message(self, format, *args):
        # Silence console log messages for a clean command-line experience
        pass

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            rendered = HTML_TEMPLATE.replace("{{DATASET_NAME}}", self.server.dataset_name)
            self.wfile.write(rendered.encode("utf-8"))
        elif self.path == "/api/runs":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            runs = []
            file_path = self.server.dataset_file
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                try:
                                    runs.append(json.loads(line))
                                except Exception:
                                    pass
                except Exception:
                    pass
            
            # Sort runs by timestamp descending (most recent first)
            runs.reverse()
            self.wfile.write(json.dumps(runs, cls=RobustEncoder).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/review":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                run_id = data.get("run_id")
                item_index = data.get("item_index", 0)
                correct = data.get("correct")
                ground_truth = data.get("ground_truth")

                from eval_factory.storage import update_run
                success = update_run(
                    dataset_name=self.server.dataset_name,
                    run_id=run_id,
                    item_index=item_index,
                    evaluation_update={"correct": correct, "ground_truth": ground_truth},
                    base_dir=self.server.base_dir
                )

                if success:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))


def find_free_port() -> int:
    """Finds an open ephemeral port on the host machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_visualizer(dataset_name: str, port: int = 0, base_dir: str = None):
    """
    Spins up the zero-dependency local dashboard server and opens the default browser.

    Args:
        dataset_name: Name of the dataset file (without .jsonl).
        port: Specific port to bind to. If 0, searches for an open port.
        base_dir: Optional directory override where datasets live.
    """
    target_dir = base_dir or config.base_dir
    safe_name = "".join([c if c.isalnum() or c in ("-", "_") else "_" for c in dataset_name])
    dataset_file = os.path.abspath(os.path.join(target_dir, f"{safe_name}.jsonl"))

    if not port:
        port = find_free_port()

    server_address = ('127.0.0.1', port)
    httpd = HTTPServer(server_address, VisualizerHTTPHandler)
    
    # Store parameters in server context for request handler access
    httpd.dataset_name = dataset_name
    httpd.dataset_file = dataset_file
    httpd.base_dir = target_dir

    url = f"http://localhost:{port}/"
    print("=" * 60)
    print(f"🚀 eval-factory visualization server starting!")
    print(f"   Dataset:  {dataset_name} ({dataset_file})")
    print(f"   Address:  {url}")
    print("=" * 60)
    print("Press Ctrl+C to terminate the visualizer...")

    # Automatically open standard browser after a tiny sleep in thread
    def open_browser():
        webbrowser.open(url)
    
    threading.Timer(0.8, open_browser).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping visualizer server...")
        httpd.server_close()
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m eval_factory.visualize <dataset_path_or_name>")
        sys.exit(1)
    
    dataset_path = sys.argv[1]
    
    # Handle files passed with extension
    if dataset_path.endswith(".jsonl"):
        dataset_path = dataset_path[:-6]
    
    # Extract base directory and actual dataset name
    base_dir = os.path.dirname(dataset_path)
    dataset_name = os.path.basename(dataset_path)
    
    # If base_dir is empty, default to None to fall back to config.base_dir
    if not base_dir:
        base_dir = None
    
    # Run server
    start_visualizer(dataset_name, base_dir=base_dir)


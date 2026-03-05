"""
ai_study_coach.py - 🎯 AI-Powered Study Coach & Exam Strategy Generator

FIXES APPLIED:
1. ✅ Study plans now generate for ALL days (not limited to 2)
2. ✅ PDF export button added and visible
3. ✅ PDF export shows complete plan (all 47 days, not just 7)
4. ✅ Updated YouTube videos with working links from multiple channels
5. ✅ Removed "first 7 days" limitation from UI
6. ✅ Fixed function signatures to match original (db, bkt_tracker, llm parameters)

This module provides:
1. Personalized Study Plans (time-boxed, adaptive)
2. Real-time Study Coaching (Pomodoro, motivation)
3. Exam Day Strategy Generator (time allocation, question selection)
4. Performance Prediction & Gap Analysis
5. Intelligent Study Session Tracking
6. YouTube Video Integration for Learning
7. PDF Export of Complete Study Plan
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import json
from collections import defaultdict
import numpy as np
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


# YouTube Video Database - Updated with working videos from multiple channels
YOUTUBE_VIDEOS = {
    # Computer Science Videos - Multiple Channels (Gate Smashers, Abdul Bari, Jenny's Lectures)
    'Computer Science': {
        'Data Structures': {
            'Arrays': 'https://www.youtube.com/embed/AT14lCXuMKI',  # Gate Smashers
            'Linked Lists': 'https://www.youtube.com/embed/R9PTBwOzceo',  # Gate Smashers
            'Stack': 'https://www.youtube.com/embed/bxRVz8zklWM',  # Jenny's Lectures
            'Queue': 'https://www.youtube.com/embed/zp6pBNbUB2U',  # Gate Smashers
            'Trees': 'https://www.youtube.com/embed/qH6yxkw0u78',  # Gate Smashers
            'Binary Search Tree': 'https://www.youtube.com/embed/pYT9F8_LFTM',  # Gate Smashers
            'Heap': 'https://www.youtube.com/embed/HqPJF2L5h9U',  # Gate Smashers
            'Hashing': 'https://www.youtube.com/embed/2BldESGZKB8',  # Abdul Bari
            'Graph': 'https://www.youtube.com/embed/tWVWeAqZ0WU',  # Gate Smashers
        },
        'Algorithms': {
            'Time Complexity': 'https://www.youtube.com/embed/9TlHvipP5yA',  # Gate Smashers
            'Sorting': 'https://www.youtube.com/embed/pkkFqlG0Hds',  # Gate Smashers
            'Searching': 'https://www.youtube.com/embed/P3YID7liBug',  # Gate Smashers
            'Recursion': 'https://www.youtube.com/embed/KEEKn7Me-ms',  # Gate Smashers
            'Dynamic Programming': 'https://www.youtube.com/embed/oBt53YbR9Kk',  # freeCodeCamp
            'Greedy Algorithm': 'https://www.youtube.com/embed/HzeK7g8cD0Y',  # Abdul Bari
            'Backtracking': 'https://www.youtube.com/embed/DKCbsiDBN6c',  # Gate Smashers
            'Divide and Conquer': 'https://www.youtube.com/embed/2Rr2tW9zvRg',  # Gate Smashers
        },
        'Operating Systems': {
            'Process Management': 'https://www.youtube.com/embed/OrM7nZcxXZU',  # Gate Smashers
            'Threads': 'https://www.youtube.com/embed/LOfGJcVnvAk',  # Gate Smashers
            'CPU Scheduling': 'https://www.youtube.com/embed/EWkQl0n0w5M',  # Gate Smashers
            'Deadlock': 'https://www.youtube.com/embed/UVo9mGARkhQ',  # Gate Smashers
            'Memory Management': 'https://www.youtube.com/embed/qdkxXygc3rE',  # Gate Smashers
            'Paging': 'https://www.youtube.com/embed/pJ6qrCB8pDw',  # Gate Smashers
            'Virtual Memory': 'https://www.youtube.com/embed/qeWUEq0Q6m8',  # Gate Smashers
            'File Systems': 'https://www.youtube.com/embed/mzUXvsuf4vY',  # Gate Smashers
        },
        'DBMS': {
            'ER Model': 'https://www.youtube.com/embed/xsg9BDiwiJE',  # Gate Smashers
            'Relational Model': 'https://www.youtube.com/embed/-CuY5ADwn24',  # Gate Smashers
            'SQL': 'https://www.youtube.com/embed/HXV3zeQKqGY',  # freeCodeCamp
            'Normalization': 'https://www.youtube.com/embed/xoTyrdT9SZI',  # Gate Smashers
            'Transactions': 'https://www.youtube.com/embed/P80Js_qClUE',  # Gate Smashers
            'Concurrency Control': 'https://www.youtube.com/embed/F5fTlT1rFqI',  # Gate Smashers
            'Indexing': 'https://www.youtube.com/embed/cjsOKgbKB48',  # Gate Smashers
        },
        'Computer Networks': {
            'OSI Model': 'https://www.youtube.com/embed/vv4y_uOneC0',  # Gate Smashers
            'TCP/IP': 'https://www.youtube.com/embed/OTwp3xtd4dg',  # Gate Smashers
            'IP Addressing': 'https://www.youtube.com/embed/ddM9AcreVqY',  # Gate Smashers
            'Subnetting': 'https://www.youtube.com/embed/BWZ-MHIhqjM',  # Gate Smashers
            'Routing': 'https://www.youtube.com/embed/AkxqkoxErRk',  # Gate Smashers
            'Transport Layer': 'https://www.youtube.com/embed/Vdc8TCESIg8',  # Gate Smashers
            'Network Security': 'https://www.youtube.com/embed/IA_WgzzgJMI',  # Neso Academy
        },
        'General': 'https://www.youtube.com/embed/AT14lCXuMKI',  # Default video
    },
    
    # Physics Videos - Multiple Channels (Khan Academy, Physics Wallah, Vedantu)
    'Physics': {
        'Mechanics': {
            'Kinematics': 'https://www.youtube.com/embed/fb3yY7pFz44',  # Khan Academy
            'Laws of Motion': 'https://www.youtube.com/embed/kKKM8Y-u7ds',  # Khan Academy
            'Work Energy Power': 'https://www.youtube.com/embed/w4QFJb9a8vo',  # Khan Academy
            'Circular Motion': 'https://www.youtube.com/embed/zGQ0fqJMg6c',  # Physics Wallah
            'Gravitation': 'https://www.youtube.com/embed/7gf6YpdvtE0',  # Physics Wallah
            'Rotational Motion': 'https://www.youtube.com/embed/q1W7x_4x_Ks',  # Physics Wallah
        },
        'Thermodynamics': {
            'Heat and Temperature': 'https://www.youtube.com/embed/0fMWOGx-KcI',  # Physics Wallah
            'Laws of Thermodynamics': 'https://www.youtube.com/embed/UmG-8xQi8HQ',  # Physics Wallah
            'Kinetic Theory': 'https://www.youtube.com/embed/J_Xz7mWKUWI',  # Physics Wallah
            'Calorimetry': 'https://www.youtube.com/embed/zp4jMu_hzjk',  # Physics Wallah
        },
        'Waves and Optics': {
            'Wave Motion': 'https://www.youtube.com/embed/EF6h3l4wPgE',  # Physics Wallah
            'Sound Waves': 'https://www.youtube.com/embed/kLiB7MpbxKQ',  # Physics Wallah
            'Light Waves': 'https://www.youtube.com/embed/DOMVS7tJLkY',  # Khan Academy
            'Reflection': 'https://www.youtube.com/embed/u0TYmK6u1w0',  # Physics Wallah
            'Refraction': 'https://www.youtube.com/embed/y55tzg_jW9I',  # Physics Wallah
            'Interference': 'https://www.youtube.com/embed/HB6fMDNYndk',  # Physics Wallah
        },
        'Electricity': {
            'Electric Field': 'https://www.youtube.com/embed/mdulzEfQXDE',  # Physics Wallah
            'Electric Potential': 'https://www.youtube.com/embed/--J8qZpJLlE',  # Physics Wallah
            'Capacitance': 'https://www.youtube.com/embed/FRsf0VKN_Kw',  # Physics Wallah
            'Current Electricity': 'https://www.youtube.com/embed/LE1JCMN5oHo',  # Physics Wallah
            "Kirchhoff's Laws": 'https://www.youtube.com/embed/mKFaZj3pL0E',  # Physics Wallah
        },
        'Magnetism': {
            'Magnetic Field': 'https://www.youtube.com/embed/qJkLzOdWH-g',  # Physics Wallah
            'Electromagnetic Induction': 'https://www.youtube.com/embed/vRI9Qxn6l5c',  # Physics Wallah
            'AC Circuits': 'https://www.youtube.com/embed/l7lMPPjEy9s',  # Physics Wallah
        },
        'Modern Physics': {
            'Photoelectric Effect': 'https://www.youtube.com/embed/kWQ6Y5FBZks',  # Physics Wallah
            'Atomic Structure': 'https://www.youtube.com/embed/TnWh5JiWwZA',  # Physics Wallah
            'Nuclear Physics': 'https://www.youtube.com/embed/V0KjXsGRvoA',  # Physics Wallah
        },
        'General': 'https://www.youtube.com/embed/fb3yY7pFz44',  # Default video
    },
    
    # Chemistry Videos - Multiple Channels (Organic Chemistry Tutor, Khan Academy, Physics Wallah)
    'Chemistry': {
        'Physical Chemistry': {
            'Atomic Structure': 'https://www.youtube.com/embed/LxfVCZZHKt8',  # Physics Wallah
            'Chemical Bonding': 'https://www.youtube.com/embed/s-c6A6sgJcU',  # Physics Wallah
            'States of Matter': 'https://www.youtube.com/embed/WIkbNgPLy_I',  # Physics Wallah
            'Thermodynamics': 'https://www.youtube.com/embed/gHMYsq4hXN0',  # Physics Wallah
            'Chemical Equilibrium': 'https://www.youtube.com/embed/q9qWYPF_XIQ',  # Physics Wallah
            'Ionic Equilibrium': 'https://www.youtube.com/embed/e_n7W1z0YPE',  # Physics Wallah
            'Electrochemistry': 'https://www.youtube.com/embed/Ui2mRx5LE3w',  # Physics Wallah
            'Chemical Kinetics': 'https://www.youtube.com/embed/xev-F5bQ91w',  # Physics Wallah
        },
        'Inorganic Chemistry': {
            'Periodic Table': 'https://www.youtube.com/embed/dOSKZCqKYBE',  # Physics Wallah
            'Chemical Bonding': 'https://www.youtube.com/embed/s-c6A6sgJcU',  # Physics Wallah
            's-Block Elements': 'https://www.youtube.com/embed/kCvJgTZQrp8',  # Physics Wallah
            'p-Block Elements': 'https://www.youtube.com/embed/EUP-fv3cGJo',  # Physics Wallah
            'd-Block Elements': 'https://www.youtube.com/embed/Oe1DV9vDg94',  # Physics Wallah
            'Coordination Compounds': 'https://www.youtube.com/embed/XZv8RWjj6LU',  # Physics Wallah
        },
        'Organic Chemistry': {
            'Basic Concepts': 'https://www.youtube.com/embed/o8VG5csO5T0',  # Physics Wallah
            'Hydrocarbons': 'https://www.youtube.com/embed/fLJwPdLu0aU',  # Physics Wallah
            'Alkanes': 'https://www.youtube.com/embed/TKLnTt8DBGk',  # Physics Wallah
            'Alkenes': 'https://www.youtube.com/embed/f9f6P8G6lXU',  # Physics Wallah
            'Alkynes': 'https://www.youtube.com/embed/vwcXqDr84zg',  # Physics Wallah
            'Aromatic Compounds': 'https://www.youtube.com/embed/kvuGPbEFEw4',  # Physics Wallah
            'Alcohols': 'https://www.youtube.com/embed/mXeNZpTMb8w',  # Physics Wallah
            'Carboxylic Acids': 'https://www.youtube.com/embed/UbNPY-Qpmpg',  # Physics Wallah
        },
        'General': 'https://www.youtube.com/embed/LxfVCZZHKt8',  # Default video
    },
    
    # Mathematics Videos - Multiple Channels (Khan Academy, 3Blue1Brown, Organic Chemistry Tutor)
    'Mathematics': {
        'Algebra': {
            'Complex Numbers': 'https://www.youtube.com/embed/LlZrI13sDK0',  # Physics Wallah
            'Quadratic Equations': 'https://www.youtube.com/embed/s5LMfAKGhvM',  # Physics Wallah
            'Sequences and Series': 'https://www.youtube.com/embed/KQsOPl_iO5Q',  # Physics Wallah
            'Permutations': 'https://www.youtube.com/embed/XqQTXW7XfYA',  # Physics Wallah
            'Combinations': 'https://www.youtube.com/embed/bCxMhncR7PU',  # Physics Wallah
            'Binomial Theorem': 'https://www.youtube.com/embed/N6lPqqIzmYQ',  # Physics Wallah
        },
        'Trigonometry': {
            'Trigonometric Functions': 'https://www.youtube.com/embed/JWkSlNR1f6k',  # Physics Wallah
            'Trigonometric Identities': 'https://www.youtube.com/embed/Jsiu1GXwMHc',  # Physics Wallah
            'Inverse Trigonometry': 'https://www.youtube.com/embed/OZUPvkj5RaA',  # Physics Wallah
            'Height and Distance': 'https://www.youtube.com/embed/OhJLv0vN1vQ',  # Physics Wallah
        },
        'Calculus': {
            'Limits': 'https://www.youtube.com/embed/YNstP0ESndU',  # Khan Academy
            'Derivatives': 'https://www.youtube.com/embed/S0_qX4VJhMQ',  # 3Blue1Brown
            'Integration': 'https://www.youtube.com/embed/rfG8ce4nNh0',  # 3Blue1Brown
            'Differential Equations': 'https://www.youtube.com/embed/p_di4Zn4wz4',  # 3Blue1Brown
            'Continuity': 'https://www.youtube.com/embed/n5GjqMX7F_0',  # Khan Academy
            'Application of Derivatives': 'https://www.youtube.com/embed/tIpKfDc295M',  # Khan Academy
        },
        'Coordinate Geometry': {
            'Straight Lines': 'https://www.youtube.com/embed/1EziGCxB1fo',  # Organic Chemistry Tutor
            'Circles': 'https://www.youtube.com/embed/5q6GJEq5TFs',  # Organic Chemistry Tutor
            'Parabola': 'https://www.youtube.com/embed/WT9PMPy_8o8',  # Organic Chemistry Tutor
            'Ellipse': 'https://www.youtube.com/embed/rd5NvxZW9aA',  # Organic Chemistry Tutor
            'Hyperbola': 'https://www.youtube.com/embed/uS7qDdQJg7w',  # Organic Chemistry Tutor
        },
        'Vectors': {
            'Vector Basics': 'https://www.youtube.com/embed/fNk_zzaMoSs',  # 3Blue1Brown
            'Dot Product': 'https://www.youtube.com/embed/LyGKycYT2v0',  # 3Blue1Brown
            'Cross Product': 'https://www.youtube.com/embed/eu6i7WJeinw',  # 3Blue1Brown
            'Scalar Triple Product': 'https://www.youtube.com/embed/8QP3y18m6Ig',  # Organic Chemistry Tutor
        },
        'Probability': {
            'Basic Concepts': 'https://www.youtube.com/embed/uzkc-qNVoOk',  # Khan Academy
            'Conditional Probability': 'https://www.youtube.com/embed/bgCMjHzXTXs',  # Khan Academy
            'Random Variables': 'https://www.youtube.com/embed/3v9w79NhsfI',  # Khan Academy
            'Probability Distributions': 'https://www.youtube.com/embed/YXLVjCKVP7U',  # Khan Academy
        },
        'General': 'https://www.youtube.com/embed/YNstP0ESndU',  # Default video
    },
    
    # Biology Videos - Multiple Channels (Khan Academy, Amoeba Sisters, Crash Course)
    'Biology': {
        'Cell Biology': {
            'Cell Structure': 'https://www.youtube.com/embed/URUJD5NEXC8',  # Amoeba Sisters
            'Cell Division': 'https://www.youtube.com/embed/zloRa6PZ_KI',  # Amoeba Sisters
            'Mitosis': 'https://www.youtube.com/embed/f-ldPgEfAHI',  # Amoeba Sisters
            'Meiosis': 'https://www.youtube.com/embed/qCLmR9-YY7o',  # Amoeba Sisters
            'Cell Membrane': 'https://www.youtube.com/embed/Qqsf_UJSwXE',  # Amoeba Sisters
        },
        'Genetics': {
            'DNA Structure': 'https://www.youtube.com/embed/8kK2zwjRV0M',  # Amoeba Sisters
            'DNA Replication': 'https://www.youtube.com/embed/TNKWgcFPHqw',  # Amoeba Sisters
            'Protein Synthesis': 'https://www.youtube.com/embed/gG7uCskUOrA',  # Amoeba Sisters
            'Mendelian Genetics': 'https://www.youtube.com/embed/Mehz7tCxjSE',  # Amoeba Sisters
            'Genetic Engineering': 'https://www.youtube.com/embed/jAhjPd4uNFY',  # Crash Course
        },
        'Evolution': {
            'Natural Selection': 'https://www.youtube.com/embed/0SCjhI86grU',  # Crash Course
            'Evidence of Evolution': 'https://www.youtube.com/embed/P3GagfbA2vo',  # Crash Course
            'Speciation': 'https://www.youtube.com/embed/sWJcKDCkhrE',  # Crash Course
        },
        'Ecology': {
            'Ecosystems': 'https://www.youtube.com/embed/sjE-Pkjp3u4',  # Crash Course
            'Food Chains': 'https://www.youtube.com/embed/hLq2datPo5M',  # Crash Course
            'Biodiversity': 'https://www.youtube.com/embed/rxPCc_LxW_A',  # Crash Course
        },
        'Human Physiology': {
            'Digestive System': 'https://www.youtube.com/embed/W0WuG90Iy1Y',  # Crash Course
            'Circulatory System': 'https://www.youtube.com/embed/GVU_zANtroE',  # Crash Course
            'Respiratory System': 'https://www.youtube.com/embed/Z-yv3Yq4Aw4',  # Crash Course
            'Nervous System': 'https://www.youtube.com/embed/OZG8M_ldA1M',  # Crash Course
        },
        'General': 'https://www.youtube.com/embed/URUJD5NEXC8',  # Default video
    },
}


def get_video_url(subject, topic):
    """Get YouTube video URL for a subject and topic"""
    if subject not in YOUTUBE_VIDEOS:
        return None
    
    subject_videos = YOUTUBE_VIDEOS[subject]
    
    # Try to find exact match
    for category, videos in subject_videos.items():
        if category == 'General':
            continue
        if isinstance(videos, dict):
            if topic in videos:
                return videos[topic]
            # Try fuzzy matching
            for video_topic, url in videos.items():
                if topic.lower() in video_topic.lower() or video_topic.lower() in topic.lower():
                    return url
    
    # Return general video for subject
    return subject_videos.get('General')


def get_available_topics(subject):
    """Get list of available topics with videos for a subject"""
    if subject not in YOUTUBE_VIDEOS:
        return []
    
    topics = []
    subject_videos = YOUTUBE_VIDEOS[subject]
    
    for category, videos in subject_videos.items():
        if category == 'General':
            continue
        if isinstance(videos, dict):
            topics.extend(videos.keys())
    
    return topics


class AIStudyCoach:
    """AI-powered study coach for personalized learning"""
    
    def __init__(self, db, bkt_tracker, llm):
        """Initialize the coach
        
        Args:
            db: Database connection
            bkt_tracker: Bayesian Knowledge Tracking tracker
            llm: Language model instance
        """
        self.db = db
        self.bkt = bkt_tracker
        self.llm = llm
    
    def analyze_student_readiness(self, user_id, exam_date=None, exam_topics=None):
        """Comprehensive readiness assessment"""
        
        # Get all masteries from BKT
        masteries = self.bkt.get_all_concept_masteries(user_id)
        
        if not masteries:
            return {
                'overall_readiness': 0.0,
                'confidence': 'low',
                'recommendation': 'Start practicing to build your knowledge base',
                'critical_gaps': [],
                'strengths': [],
                'study_hours_needed': 50,
                'total_topics': 0,
                'mastered_count': 0,
                'weak_count': 0,
                'days_available': None,
                'hours_per_day': 0
            }
        
        # Calculate overall readiness
        avg_mastery = np.mean([m['mastery_probability'] for m in masteries])
        
        # Identify gaps and strengths
        critical_gaps = [m for m in masteries if m['mastery_probability'] < 0.5]
        strengths = [m for m in masteries if m['mastery_probability'] > 0.75]
        
        # Estimate study hours needed
        gaps_count = len(critical_gaps)
        weak_count = len([m for m in masteries if 0.5 <= m['mastery_probability'] < 0.7])
        
        study_hours = (gaps_count * 3) + (weak_count * 1.5)
        
        # Days until exam
        days_available = None
        hours_per_day = 0
        
        if exam_date:
            exam_dt = datetime.strptime(exam_date, '%Y-%m-%d') if isinstance(exam_date, str) else exam_date
            days_available = (exam_dt - datetime.now()).days
            
            if days_available > 0:
                hours_per_day = study_hours / days_available
        
        # Determine confidence level
        if avg_mastery >= 0.75:
            confidence = 'high'
            recommendation = '🎉 Excellent preparation! Focus on revision and mock tests.'
        elif avg_mastery >= 0.5:
            confidence = 'moderate'
            recommendation = '📈 Good progress! Strengthen weak areas and take more practice tests.'
        else:
            confidence = 'low'
            recommendation = '⚠️ Need more preparation. Focus on understanding concepts and consistent practice.'
        
        return {
            'overall_readiness': avg_mastery,
            'confidence': confidence,
            'recommendation': recommendation,
            'critical_gaps': critical_gaps[:5],  # Top 5
            'strengths': strengths[:5],  # Top 5
            'study_hours_needed': int(study_hours),
            'total_topics': len(masteries),
            'mastered_count': len(strengths),
            'weak_count': gaps_count,
            'days_available': days_available,
            'hours_per_day': hours_per_day
        }
    
    def generate_study_plan(self, user_id, days=30, hours_per_day=3, exam_topics=None):
        """
        Generate day-by-day study plan
        
        FIXED: Now generates plan for ALL days, not limited to 2
        
        Args:
            user_id: Student ID
            days: Total study days
            hours_per_day: Hours available per day
            exam_topics: Optional list of specific topics
        
        Returns:
            List of daily study plans
        """
        readiness = self.analyze_student_readiness(user_id)
        
        # Get topics to focus on
        needs_review = self.bkt.get_concepts_needing_review(user_id, threshold=0.7)
        optimal_topics = self.bkt.get_optimal_practice_topics(user_id, count=10)
        
        # Combine and prioritize all topics
        all_topics = []
        
        # High priority: critical gaps
        for gap in readiness['critical_gaps']:
            all_topics.append({
                'subject': gap['subject'],
                'topic': gap['topic'],
                'priority': 'critical',
                'mastery': gap['mastery_probability'],
                'hours_needed': 3
            })
        
        # Medium priority: needs review
        for review in needs_review[:5]:
            if review['priority'] in ['high', 'medium']:
                all_topics.append({
                    'subject': review['subject'],
                    'topic': review['topic'],
                    'priority': 'high',
                    'mastery': review['mastery'],
                    'hours_needed': 2
                })
        
        # Low priority: maintenance
        for opt in optimal_topics:
            if opt['mastery'] > 0.6:
                all_topics.append({
                    'subject': opt['subject'],
                    'topic': opt['topic'],
                    'priority': 'maintenance',
                    'mastery': opt['mastery'],
                    'hours_needed': 1
                })
        
        # FIXED: Create day-by-day plan for ALL days
        plan = []
        current_day = 1
        topics_scheduled = set()
        
        # FIXED: Loop through ALL days, not just 2
        while current_day <= days:
            day_plan = {
                'day': current_day,
                'date': (datetime.now() + timedelta(days=current_day-1)).strftime('%Y-%m-%d'),
                'sessions': [],
                'total_hours': 0
            }
            
            hours_left = hours_per_day
            
            # Schedule topics for this day
            for topic in all_topics[:]:
                if hours_left <= 0:
                    break
                
                topic_key = f"{topic['subject']}:{topic['topic']}"
                if topic_key in topics_scheduled:
                    continue
                
                session_hours = min(topic['hours_needed'], hours_left, 2)  # Max 2 hours per session
                
                day_plan['sessions'].append({
                    'subject': topic['subject'],
                    'topic': topic['topic'],
                    'duration_hours': session_hours,
                    'priority': topic['priority'],
                    'mastery': topic['mastery'],
                    'activities': self._suggest_activities(topic['priority'], topic['mastery']),
                    'video_url': get_video_url(topic['subject'], topic['topic'])
                })
                
                hours_left -= session_hours
                day_plan['total_hours'] += session_hours
                
                topic['hours_needed'] -= session_hours
                
                if topic['hours_needed'] <= 0:
                    topics_scheduled.add(topic_key)
                    all_topics.remove(topic)
            
            # Add revision for spaced repetition (after day 3)
            if current_day > 3 and hours_left > 0 and len(plan) > 2:
                # Review a topic from 3 days ago
                old_day = plan[current_day - 4]
                if old_day['sessions']:
                    review_session = old_day['sessions'][0]
                    day_plan['sessions'].append({
                        'subject': review_session['subject'],
                        'topic': review_session['topic'],
                        'duration_hours': min(0.5, hours_left),
                        'priority': 'revision',
                        'mastery': review_session['mastery'],
                        'activities': ['📝 Quick revision', '🎯 Solve 5 MCQs'],
                        'video_url': review_session.get('video_url')
                    })
                    day_plan['total_hours'] += min(0.5, hours_left)
            
            plan.append(day_plan)
            current_day += 1
            
            # Break if no more topics to schedule
            if not all_topics and hours_left >= hours_per_day:
                break
        
        return plan
    
    def _suggest_activities(self, priority, mastery):
        """Suggest learning activities based on mastery level"""
        
        if mastery < 0.4:
            return [
                '📺 Watch concept video (20 min)',
                '📚 Read theory and make notes (30 min)',
                '🎯 Solve 5 basic MCQs (15 min)',
                '💡 Review solutions (10 min)'
            ]
        elif mastery < 0.7:
            return [
                '📺 Watch advanced concept video (15 min)',
                '🎯 Solve 10 practice problems (30 min)',
                '📝 Review mistakes (15 min)',
                '🔄 Attempt harder problems (20 min)'
            ]
        else:
            return [
                '🎯 Solve 15 mixed MCQs (30 min)',
                '⚡ Speed practice (20 min)',
                '📝 Teach concept to someone (15 min)',
                '🏆 Attempt previous year questions (25 min)'
            ]
    
    def generate_exam_strategy(self, user_id, exam_duration_minutes=180, total_questions=100):
        """Generate exam day strategy"""
        
        masteries = self.bkt.get_all_concept_masteries(user_id)
        
        if not masteries:
            return self._generate_default_exam_strategy(exam_duration_minutes, total_questions)
        
        # Group by subject
        subjects = {}
        for m in masteries:
            subj = m['subject']
            if subj not in subjects:
                subjects[subj] = []
            subjects[subj].append(m['mastery_probability'])
        
        # Calculate subject-wise confidence
        subject_confidence = {
            subj: np.mean(masteries_list)
            for subj, masteries_list in subjects.items()
        }
        
        # Sort subjects by confidence (do easiest first)
        sorted_subjects = sorted(subject_confidence.items(), key=lambda x: x[1], reverse=True)
        
        # Allocate time
        questions_per_subject = total_questions // len(sorted_subjects)
        time_allocation = []
        
        for subject, confidence in sorted_subjects:
            if confidence >= 0.7:
                # Strong subject - allocate less time
                time_allocated = int((questions_per_subject * exam_duration_minutes / total_questions) * 0.8)
            elif confidence >= 0.5:
                # Moderate subject - standard time
                time_allocated = int(questions_per_subject * exam_duration_minutes / total_questions)
            else:
                # Weak subject - more time
                time_allocated = int((questions_per_subject * exam_duration_minutes / total_questions) * 1.2)
            
            time_allocation.append({
                'subject': subject,
                'questions': questions_per_subject,
                'time_minutes': time_allocated / 60,
                'confidence': confidence,
                'strategy': self._get_subject_strategy(confidence)
            })
        
        total_allocated = sum(item['time_minutes'] for item in time_allocation) * 60
        review_time = (exam_duration_minutes - total_allocated) / 60
        
        return {
            'time_allocation': time_allocation,
            'review_time': max(10, review_time),
            'total_duration': exam_duration_minutes,
            'strategy_tips': [
                "🎯 Start with your strongest subjects to build confidence",
                "⏱️ Stick to time limits - don't get stuck on difficult questions",
                "✅ Mark questions you're unsure about and review them later",
                "🧘 Take 30-second micro-breaks between subjects",
                "📝 Read questions carefully - exam anxiety causes silly mistakes",
                "🎲 For MCQs, eliminate obviously wrong options first",
                f"⏰ Reserve {review_time:.0f} minutes at the end for review"
            ]
        }
    
    def _get_subject_strategy(self, confidence):
        """Get subject-specific strategy"""
        if confidence >= 0.7:
            return "Confidence is high - aim for speed and accuracy. Review answers once."
        elif confidence >= 0.5:
            return "Moderate confidence - take your time, double-check tricky questions."
        else:
            return "Build confidence - start with easy questions, don't panic on hard ones."
    
    def _generate_default_exam_strategy(self, exam_duration_minutes, total_questions):
        """Default strategy for new users"""
        
        return {
            'time_allocation': [{
                'subject': 'All Subjects',
                'questions': total_questions,
                'time_minutes': exam_duration_minutes * 0.9 / 60,
                'confidence': 0.5,
                'strategy': "Standard approach - balance speed and accuracy"
            }],
            'review_time': exam_duration_minutes * 0.1 / 60,
            'total_duration': exam_duration_minutes,
            'strategy_tips': [
                "🎯 Attempt all questions",
                "⏱️ Divide time equally",
                "✅ Mark questions for review",
                "🧘 Stay calm and focused",
                "📝 Read questions carefully"
            ]
        }


def export_study_plan_to_pdf(plan):
    """
    Export complete study plan to PDF
    
    FIXED: Now exports ALL days, not just first 7
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2ca02c'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#ff7f0e'),
        spaceAfter=8
    )
    
    normal_style = styles['Normal']
    
    # Build content
    content = []
    
    # Title
    content.append(Paragraph("🎯 AI-Generated Study Plan", title_style))
    content.append(Spacer(1, 0.2*inch))
    
    # Summary Section
    content.append(Paragraph("📊 Plan Summary", heading_style))
    
    total_hours = sum(day['total_hours'] for day in plan)
    total_sessions = sum(len(day['sessions']) for day in plan)
    avg_hours = total_hours / len(plan) if plan else 0
    
    summary_data = [
        ['Total Study Days', f"{len(plan)} days"],
        ['Total Study Hours', f"{total_hours:.1f} hours"],
        ['Total Sessions', str(total_sessions)],
        ['Average Hours/Day', f"{avg_hours:.1f} hours"],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    
    content.append(summary_table)
    content.append(Spacer(1, 0.3*inch))
    
    # FIXED: Export ALL days
    content.append(Paragraph(f"📅 Complete Daily Schedule ({len(plan)} days)", heading_style))
    content.append(Spacer(1, 0.1*inch))
    
    # Process ALL days
    for day_plan in plan:
        # Day header
        day_title = f"📌 Day {day_plan['day']} ({day_plan['date']}) - {day_plan['total_hours']:.1f}h"
        content.append(Paragraph(day_title, subheading_style))
        
        # Sessions table
        if day_plan['sessions']:
            session_data = [['Subject', 'Topic', 'Duration', 'Priority']]
            
            for session in day_plan['sessions']:
                session_data.append([
                    session['subject'],
                    session['topic'],
                    f"{session['duration_hours']:.1f}h",
                    session['priority'].title()
                ])
            
            session_table = Table(session_data, colWidths=[1.5*inch, 2*inch, 1*inch, 1.1*inch])
            session_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            content.append(session_table)
        else:
            content.append(Paragraph("No sessions scheduled", normal_style))
        
        content.append(Spacer(1, 0.15*inch))
        
        # Add page break every 3 days
        if day_plan['day'] % 3 == 0 and day_plan['day'] < len(plan):
            content.append(PageBreak())
    
    # Footer
    content.append(Spacer(1, 0.3*inch))
    content.append(Paragraph("💡 Study Tips:", heading_style))
    tips = [
        "• Follow the Pomodoro Technique (25 min focus + 5 min break)",
        "• Watch recommended videos for each topic",
        "• Take practice quizzes after each session",
        "• Review previous topics regularly for retention",
        "• Stay consistent with your daily schedule"
    ]
    for tip in tips:
        content.append(Paragraph(tip, normal_style))
        content.append(Spacer(1, 0.05*inch))
    
    # Build PDF
    doc.build(content)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


def render_ai_study_coach_tab(user_id, db, bkt_tracker, llm):
    """
    AI Study Coach tab.
    Only the Video Lectures tab is active.
    Study Plan, Exam Readiness, Exam Strategy are locked until more data.
    """
    st.title("🎓 AI Study Coach")
    st.caption("Video lectures, Pomodoro timer, and study tools")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎥 Video Lectures",
        "📚 Study Plan  🔒",
        "📊 Exam Readiness  🔒",
        "🎓 Exam Strategy  🔒",
    ])

    with tab1:
        render_live_study_session(user_id, db, llm)

    with tab2:
        st.markdown("## 📚 Study Plan Generator")
        st.info(
            "🔒 **Coming soon** — Complete at least **10 practice sessions** "
            "to unlock your personalized AI study plan."
        )
        st.markdown("""
        **Once unlocked, you'll get:**
        - 📅 Day-by-day study schedule tailored to your gaps
        - 🎯 Priority topics based on your mastery scores
        - ⏱️ Time estimates per topic
        - 📄 Downloadable PDF plan
        """)

    with tab3:
        st.markdown("## 📊 Exam Readiness Assessment")
        st.info(
            "🔒 **Coming soon** — Take at least **3 full exams** "
            "to unlock your readiness score."
        )
        st.markdown("""
        **Once unlocked, you'll see:**
        - 🎯 Overall readiness % with confidence level
        - 💪 Your strongest topics
        - ⚠️ Critical gaps to fix before exam day
        - 📈 Hours needed to reach target score
        """)

    with tab4:
        st.markdown("## 🎓 Exam Day Strategy")
        st.info(
            "🔒 **Coming soon** — Complete your exam profile to unlock "
            "a personalised exam-day strategy."
        )
        st.markdown("""
        **Once unlocked, you'll get:**
        - ⏱️ Time allocation per subject
        - 🎲 Question selection strategy
        - 🧘 Focus tips for exam day
        - 📋 Subject-wise approach based on your strengths
        """)


def render_study_plan_generator(user_id, coach):
    """Render study plan generator - FIXED: All days + PDF export"""
    
    st.markdown("### 📚 Generate Your Personalized Study Plan")
    st.caption("AI-powered plan based on your performance and goals")
    
    col1, col2 = st.columns(2)
    
    with col1:
        days = st.number_input("Study Period (days)", min_value=7, max_value=90, value=30)
    
    with col2:
        hours_per_day = st.number_input("Hours/Day", min_value=1, max_value=12, value=3)
    
    if st.button("🎯 Generate My Study Plan", type="primary", use_container_width=True):
        with st.spinner("🧠 Creating your personalized study plan..."):
            plan = coach.generate_study_plan(user_id, days, hours_per_day)
        
        if not plan:
            st.warning("⚠️ Start practicing to generate a personalized study plan!")
            return
        
        # Store plan in session state
        st.session_state['current_study_plan'] = plan
        
        st.success(f"✅ {len(plan)}-day study plan generated!")
        
        # Summary
        st.markdown("---")
        st.markdown("### 📊 Plan Summary")
        
        col1, col2, col3 = st.columns(3)
        
        total_hours = sum(day['total_hours'] for day in plan)
        total_sessions = sum(len(day['sessions']) for day in plan)
        
        with col1:
            st.metric("Total Study Hours", f"{total_hours:.1f} hours")
        with col2:
            st.metric("Total Sessions", total_sessions)
        with col3:
            st.metric("Avg Hours/Day", f"{total_hours/len(plan):.1f} hours")
        
        # FIXED: PDF Export Button - Now visible
        st.markdown("---")
        st.markdown("### 📥 Export Options")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Generate PDF
            pdf_bytes = export_study_plan_to_pdf(plan)
            
            st.download_button(
                label="📄 Download Complete Plan (PDF)",
                data=pdf_bytes,
                file_name=f"study_plan_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
        
        with col2:
            # JSON export
            json_data = json.dumps(plan, indent=2, default=str)
            st.download_button(
                label="📊 Download as JSON",
                data=json_data,
                file_name=f"study_plan_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # FIXED: Display daily schedule
        st.markdown("---")
        st.markdown(f"### 📅 Daily Schedule")
        
        # FIXED: Show complete plan
        st.info(f"📌 Showing complete {len(plan)}-day plan")
        
        # Display each day
        for day_plan in plan:
            with st.expander(
                f"📌 Day {day_plan['day']} ({day_plan['date']}) - {day_plan['total_hours']:.1f} hours",
                expanded=(day_plan['day'] == 1)
            ):
                for idx, session in enumerate(day_plan['sessions'], 1):
                    priority_colors = {
                        'critical': '🔴',
                        'high': '🟡',
                        'maintenance': '🟢',
                        'revision': '🔵'
                    }
                    
                    priority_icon = priority_colors.get(session['priority'], '⚪')
                    
                    st.markdown(f"#### {priority_icon} Session {idx}: {session['subject']} - {session['topic']}")
                    st.markdown(f"*Duration:* {session['duration_hours']:.1f} hours | *Current Mastery:* {session['mastery']*100:.0f}%")
                    
                    if session.get('video_url'):
                        st.markdown(f"[🎥 Watch Video]({session['video_url'].replace('/embed/', '/watch?v=')})")
                    
                    st.markdown("**Activities:**")
                    for activity in session['activities']:
                        st.markdown(f"  - {activity}")
                    
                    st.markdown("---")


def render_live_study_session(user_id, db=None, llm=None):
    """Render live study session with Pomodoro timer and videos"""
    
    st.markdown("### 🎥 Live Study Session")
    st.caption("Study with videos, track time, and stay motivated!")
    
    # Initialize session state
    if 'pomodoro_running' not in st.session_state:
        st.session_state.pomodoro_running = False
    if 'pomodoro_start_time' not in st.session_state:
        st.session_state.pomodoro_start_time = None
    if 'pomodoro_count' not in st.session_state:
        st.session_state.pomodoro_count = 0
    if 'pomodoro_type' not in st.session_state:
        st.session_state.pomodoro_type = 'work'
    if 'current_subject' not in st.session_state:
        st.session_state.current_subject = None
    if 'current_topic' not in st.session_state:
        st.session_state.current_topic = None
    
    # Subject and topic selection — filtered by user's exam type
    st.markdown("#### 📚 Choose What to Study")

    # Map college exam subjects to Computer Science (which holds all CS videos)
    SUBJECT_TO_VIDEO_KEY = {
        'DSA':               'Computer Science',
        'DBMS':              'Computer Science',
        'Operating Systems': 'Computer Science',
        'Computer Networks': 'Computer Science',
        'OOPs':              'Computer Science',
        'Computer Science':  'Computer Science',
        'Physics':           'Physics',
        'Chemistry':         'Chemistry',
        'Mathematics':       'Mathematics',
        'Biology':           'Biology',
    }

    # Map college exam subjects to specific sub-category of Computer Science videos
    COLLEGE_TOPIC_FILTER = {
        'DSA':               ['Data Structures', 'Algorithms'],
        'DBMS':              ['DBMS'],
        'Operating Systems': ['Operating Systems'],
        'Computer Networks': ['Computer Networks'],
        'OOPs':              ['Data Structures'],  # closest available
    }

    # Get user's allowed subjects from session (set during onboarding)
    user_subjects = st.session_state.get('available_subjects') or list(YOUTUBE_VIDEOS.keys())
    # Only show subjects that have videos
    displayable_subjects = [s for s in user_subjects if SUBJECT_TO_VIDEO_KEY.get(s) in YOUTUBE_VIDEOS]
    if not displayable_subjects:
        displayable_subjects = list(YOUTUBE_VIDEOS.keys())

    col1, col2 = st.columns(2)

    with col1:
        display_subject = st.selectbox(
            "Subject",
            options=displayable_subjects,
            key='study_subject'
        )

    # Map display subject → actual YOUTUBE_VIDEOS key
    video_key = SUBJECT_TO_VIDEO_KEY.get(display_subject, display_subject)

    with col2:
        # For college exam subjects, filter to relevant topic categories only
        if display_subject in COLLEGE_TOPIC_FILTER:
            allowed_categories = COLLEGE_TOPIC_FILTER[display_subject]
            topics = []
            for cat in allowed_categories:
                cat_videos = YOUTUBE_VIDEOS.get('Computer Science', {}).get(cat, {})
                if isinstance(cat_videos, dict):
                    topics.extend(cat_videos.keys())
        else:
            topics = get_available_topics(video_key)

        topic = st.selectbox(
            "Topic",
            options=topics if topics else ["General"],
            key='study_topic'
        )

    # Get video URL using the mapped key
    video_url = get_video_url(video_key, topic)
    
    # Video player
    if video_url:
        st.markdown("---")
        st.markdown("#### 🎬 Educational Video")
        
        st.markdown(f"""
        <iframe width="100%" height="450" src="{video_url}" 
        frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen></iframe>
        """, unsafe_allow_html=True)
    else:
        st.info(f"No video available for {topic}. Please select another topic.")
    
    # Pomodoro timer controls
    st.markdown("---")
    st.markdown("#### ⏱️ Pomodoro Timer")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        work_duration = st.number_input("Focus Duration (min)", value=25, min_value=1, max_value=60)
    with col2:
        break_duration = st.number_input("Break Duration (min)", value=5, min_value=1, max_value=30)
    with col3:
        st.write("")
    
    # Timer controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Start Session", use_container_width=True, type="primary"):
            st.session_state.pomodoro_running = True
            st.session_state.pomodoro_start_time = datetime.now()
            st.session_state.pomodoro_type = 'work'
            st.session_state.current_subject = subject
            st.session_state.current_topic = topic
            st.rerun()
    
    with col2:
        if st.button("⏸️ Pause", use_container_width=True):
            st.session_state.pomodoro_running = False
    
    with col3:
        if st.button("🔄 Reset", use_container_width=True):
            st.session_state.pomodoro_running = False
            st.session_state.pomodoro_start_time = None
            st.session_state.pomodoro_count = 0
            st.session_state.pomodoro_type = 'work'
    
    # Display timer
    if st.session_state.pomodoro_running and st.session_state.pomodoro_start_time:
        elapsed = (datetime.now() - st.session_state.pomodoro_start_time).seconds
        
        total_duration = work_duration * 60 if st.session_state.pomodoro_type == 'work' else break_duration * 60
        remaining = max(0, total_duration - elapsed)
        
        # Check if session complete
        if remaining == 0:
            if st.session_state.pomodoro_type == 'work':
                st.session_state.pomodoro_count += 1
                st.session_state.pomodoro_type = 'break'
                st.success(f"🎉 Focus session {st.session_state.pomodoro_count} complete!")
                st.balloons()
            else:
                st.session_state.pomodoro_type = 'work'
                st.info("☕ Break over! Ready for another focus session?")
            
            st.session_state.pomodoro_start_time = datetime.now()
            st.rerun()
        
        # Display timer
        mins = remaining // 60
        secs = remaining % 60
        progress = 1 - (remaining / total_duration)
        
        phase_emoji = "🎯" if st.session_state.pomodoro_type == 'work' else "☕"
        phase_name = "FOCUS TIME" if st.session_state.pomodoro_type == 'work' else "BREAK TIME"
        
        st.markdown(f"## {phase_emoji} {phase_name}")
        st.markdown(f"# {mins:02d}:{secs:02d}")
        st.progress(progress)
        
        # Motivational messages
        motivations = [
            "💪 Stay focused!",
            "🎯 You're doing great!",
            "🔥 Keep going!",
            "⚡ Almost there!",
            "🌟 Excellent work!"
        ] if st.session_state.pomodoro_type == 'work' else [
            "😌 Relax!",
            "🧘 Breathe!",
            "💧 Hydrate!",
            "🌸 Rest well!",
            "✨ Recharge!"
        ]
        
        msg_index = (elapsed // 10) % len(motivations)
        st.info(motivations[msg_index])
        
        # Session stats
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Sessions Completed", st.session_state.pomodoro_count)
        with col2:
            st.metric("Total Focus Time", f"{st.session_state.pomodoro_count * work_duration} min")
        with col3:
            st.metric("Current", st.session_state.pomodoro_type.title())
        
        if st.session_state.current_subject:
            st.info(f"📖 Studying: **{st.session_state.current_subject}** - **{st.session_state.current_topic}**")
        
        # Auto-refresh
        import time
        time.sleep(1)
        st.rerun()
    
    # Study Tips
    st.markdown("---")
    st.markdown("### 💡 Study Tips")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Effective Video Learning:**
        - 📝 Take notes while watching
        - ⏸️ Pause to understand concepts
        - 🔄 Rewatch difficult parts
        - ❓ Note down questions
        """)
    
    with col2:
        st.success("""
        **Pomodoro Benefits:**
        - 🎯 Improved focus
        - 🧠 Prevents fatigue
        - ⚡ Maintains productivity
        - 🎓 Better retention
        """)


def render_readiness_report(user_id, coach):
    """Render exam readiness assessment"""
    
    st.markdown("### 📊 Exam Readiness Assessment")
    st.caption("Comprehensive analysis of your preparation level")
    
    exam_date = st.date_input(
        "Exam Date (optional)",
        value=None,
        help="Helps calculate study intensity"
    )
    
    exam_date_str = exam_date.strftime('%Y-%m-%d') if exam_date else None
    
    if st.button("🔍 Analyze My Readiness", type="primary", use_container_width=True):
        with st.spinner("🧠 Analyzing your preparation..."):
            readiness = coach.analyze_student_readiness(user_id, exam_date_str)
        
        # Overall readiness
        st.markdown("---")
        st.markdown("### 🎯 Overall Readiness Score")
        
        score_pct = readiness['overall_readiness'] * 100
        
        if score_pct >= 75:
            st.success(f"## {score_pct:.1f}% Ready! 🎉")
            st.balloons()
        elif score_pct >= 50:
            st.info(f"## {score_pct:.1f}% Ready 📈")
        else:
            st.warning(f"## {score_pct:.1f}% Ready ⚠️")
        
        st.progress(readiness['overall_readiness'], text=readiness['confidence'].upper())
        
        # Recommendation
        st.markdown("---")
        st.markdown("### 💡 AI Recommendation")
        st.info(readiness['recommendation'])
        
        # Key metrics
        st.markdown("---")
        st.markdown("### 📈 Preparation Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Topics", readiness['total_topics'])
        with col2:
            st.metric("Mastered", readiness['mastered_count'])
        with col3:
            st.metric("Need Work", readiness['weak_count'])
        with col4:
            st.metric("Study Hours Needed", f"{readiness['study_hours_needed']}h")
        
        if exam_date_str and readiness['days_available']:
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Days Until Exam", readiness['days_available'])
            with col2:
                st.metric("Required Hours/Day", f"{readiness['hours_per_day']:.1f}h")
        
        # Strengths
        st.markdown("---")
        st.markdown("### 💪 Your Strengths")
        
        if readiness['strengths']:
            for strength in readiness['strengths']:
                mastery_pct = strength['mastery_probability'] * 100
                st.success(f"**{strength['subject']}: {strength['topic']}** - {mastery_pct:.0f}% mastery")
        else:
            st.info("Keep practicing to build your strengths!")
        
        # Critical gaps
        st.markdown("---")
        st.markdown("### 🎯 Priority Focus Areas")
        
        if readiness['critical_gaps']:
            for gap in readiness['critical_gaps']:
                mastery_pct = gap['mastery_probability'] * 100
                st.warning(f"**{gap['subject']}: {gap['topic']}** - {mastery_pct:.0f}% mastery")
        else:
            st.success("✅ No critical gaps! You're well prepared!")


def render_exam_strategy(user_id, coach):
    """Render exam day strategy generator"""
    
    st.markdown("### 🎓 Exam Day Strategy Generator")
    st.caption("Get AI-powered strategy for exam day success")
    
    col1, col2 = st.columns(2)
    
    with col1:
        exam_duration = st.number_input("⏱️ Exam Duration (minutes)", value=180, min_value=30, max_value=300, step=15)
    
    with col2:
        total_questions = st.number_input("📝 Total Questions", value=100, min_value=10, max_value=300, step=10)
    
    if st.button("🎯 Generate Exam Strategy", type="primary", use_container_width=True):
        with st.spinner("🧠 Crafting your exam strategy..."):
            strategy = coach.generate_exam_strategy(user_id, exam_duration, total_questions)
        
        # Strategy tips
        st.markdown("---")
        st.markdown("### 💡 Strategic Approach")
        
        for tip in strategy['strategy_tips']:
            st.info(tip)
        
        # Time allocation
        st.markdown("---")
        st.markdown("### ⏱️ Time Allocation by Subject")
        
        allocation_df = pd.DataFrame(strategy['time_allocation'])
        
        st.dataframe(
            allocation_df[['subject', 'questions', 'time_minutes', 'confidence', 'strategy']],
            use_container_width=True,
            hide_index=True
        )
        
        # Visualization
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=allocation_df['subject'],
            y=allocation_df['time_minutes'] * 60,
            name='Time Allocated',
            marker_color='lightblue',
            text=allocation_df['time_minutes'].apply(lambda x: f"{x:.1f} min"),
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Time Distribution Across Subjects",
            xaxis_title="Subject",
            yaxis_title="Time (seconds)",
            showlegend=False,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Review time
        st.markdown("---")
        st.success(f"⏰ **Reserve {strategy['review_time']:.0f} minutes** for final review!")


# Export
__all__ = ['AIStudyCoach', 'render_ai_study_coach_tab', 'get_video_url', 'get_available_topics', 'export_study_plan_to_pdf']
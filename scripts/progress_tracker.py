#!/usr/bin/env python3
"""Progress tracking system for Rick Rubin data collection."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProgressTracker:
    """Track collection, processing, and export progress."""
    
    def __init__(self, db_path: str = "data/progress.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Collection progress table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS collection_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    url TEXT UNIQUE,
                    file_path TEXT,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    word_count INTEGER,
                    quality_score REAL,
                    status TEXT DEFAULT 'collected',
                    included_in_training BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Processing status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    cleaned_at TIMESTAMP,
                    formatted_at TIMESTAMP,
                    exported_at TIMESTAMP,
                    export_file TEXT,
                    training_examples INTEGER,
                    FOREIGN KEY (source_id) REFERENCES collection_progress (id)
                )
            """)
            
            # Quality metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quality_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER,
                    rick_score REAL,
                    production_score REAL,
                    album_mentions INTEGER,
                    artist_mentions INTEGER,
                    overall_score REAL,
                    FOREIGN KEY (source_id) REFERENCES collection_progress (id)
                )
            """)
            
            # Export history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS export_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    export_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    export_file TEXT,
                    total_examples INTEGER,
                    avg_quality_score REAL,
                    min_quality_threshold REAL,
                    sources_included INTEGER
                )
            """)
            
            conn.commit()
    
    def record_collection(self, source_type: str, source_name: str, 
                         file_path: str, word_count: int, 
                         quality_score: float, url: Optional[str] = None) -> int:
        """Record a new transcript collection."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO collection_progress 
                    (source_type, source_name, url, file_path, word_count, quality_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (source_type, source_name, url, file_path, word_count, quality_score))
                
                source_id = cursor.lastrowid
                logger.info(f"Recorded collection: {source_name} (ID: {source_id})")
                return source_id
                
            except sqlite3.IntegrityError:
                # URL already exists
                cursor.execute("""
                    SELECT id FROM collection_progress WHERE url = ?
                """, (url,))
                existing_id = cursor.fetchone()[0]
                logger.warning(f"Collection already exists for URL: {url} (ID: {existing_id})")
                return existing_id
    
    def record_quality_metrics(self, source_id: int, metrics: Dict[str, float]):
        """Record detailed quality metrics for a source."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO quality_metrics
                (source_id, rick_score, production_score, album_mentions, 
                 artist_mentions, overall_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source_id,
                metrics.get('rick_score', 0),
                metrics.get('production_score', 0),
                metrics.get('album_mentions', 0),
                metrics.get('artist_mentions', 0),
                metrics.get('overall_score', 0)
            ))
    
    def update_processing_status(self, source_id: int, stage: str):
        """Update processing status for a source."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if processing record exists
            cursor.execute("""
                SELECT id FROM processing_status WHERE source_id = ?
            """, (source_id,))
            
            if cursor.fetchone() is None:
                cursor.execute("""
                    INSERT INTO processing_status (source_id) VALUES (?)
                """, (source_id,))
            
            # Update appropriate timestamp
            column_map = {
                'cleaned': 'cleaned_at',
                'formatted': 'formatted_at',
                'exported': 'exported_at'
            }
            
            if stage in column_map:
                cursor.execute(f"""
                    UPDATE processing_status 
                    SET {column_map[stage]} = CURRENT_TIMESTAMP
                    WHERE source_id = ?
                """, (source_id,))
    
    def record_export(self, export_file: str, total_examples: int,
                     avg_quality: float, min_threshold: float, 
                     sources_included: int):
        """Record an export operation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO export_history
                (export_file, total_examples, avg_quality_score, 
                 min_quality_threshold, sources_included)
                VALUES (?, ?, ?, ?, ?)
            """, (export_file, total_examples, avg_quality, min_threshold, sources_included))
    
    def get_collection_stats(self) -> Dict:
        """Get overall collection statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total collections
            cursor.execute("SELECT COUNT(*) FROM collection_progress")
            total_collections = cursor.fetchone()[0]
            
            # By source type
            cursor.execute("""
                SELECT source_type, COUNT(*), SUM(word_count)
                FROM collection_progress
                GROUP BY source_type
            """)
            by_type = cursor.fetchall()
            
            # Quality distribution
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN quality_score >= 90 THEN 1 END) as excellent,
                    COUNT(CASE WHEN quality_score >= 80 AND quality_score < 90 THEN 1 END) as good,
                    COUNT(CASE WHEN quality_score >= 70 AND quality_score < 80 THEN 1 END) as fair,
                    COUNT(CASE WHEN quality_score < 70 THEN 1 END) as poor
                FROM collection_progress
            """)
            quality_dist = cursor.fetchone()
            
            # Processing status
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT source_id) as cleaned,
                    COUNT(DISTINCT CASE WHEN formatted_at IS NOT NULL THEN source_id END) as formatted,
                    COUNT(DISTINCT CASE WHEN exported_at IS NOT NULL THEN source_id END) as exported
                FROM processing_status
            """)
            processing = cursor.fetchone()
            
            return {
                'total_collections': total_collections,
                'by_source_type': {row[0]: {'count': row[1], 'words': row[2] or 0} 
                                  for row in by_type},
                'quality_distribution': {
                    'excellent': quality_dist[0],
                    'good': quality_dist[1],
                    'fair': quality_dist[2],
                    'poor': quality_dist[3]
                },
                'processing_status': {
                    'cleaned': processing[0] if processing else 0,
                    'formatted': processing[1] if processing else 0,
                    'exported': processing[2] if processing else 0
                }
            }
    
    def get_pending_processing(self, stage: str = 'cleaned') -> List[Dict]:
        """Get sources pending a specific processing stage."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            stage_column = {
                'cleaned': 'cleaned_at',
                'formatted': 'formatted_at',
                'exported': 'exported_at'
            }.get(stage, 'cleaned_at')
            
            cursor.execute(f"""
                SELECT c.id, c.source_name, c.file_path, c.quality_score
                FROM collection_progress c
                LEFT JOIN processing_status p ON c.id = p.source_id
                WHERE p.{stage_column} IS NULL OR p.id IS NULL
                ORDER BY c.quality_score DESC
            """)
            
            return [
                {
                    'id': row[0],
                    'source_name': row[1],
                    'file_path': row[2],
                    'quality_score': row[3]
                }
                for row in cursor.fetchall()
            ]
    
    def get_high_quality_sources(self, min_score: float = 80.0) -> List[Dict]:
        """Get sources above a quality threshold."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.*, q.rick_score, q.production_score
                FROM collection_progress c
                LEFT JOIN quality_metrics q ON c.id = q.source_id
                WHERE c.quality_score >= ?
                ORDER BY c.quality_score DESC
            """, (min_score,))
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def generate_report(self) -> str:
        """Generate a comprehensive progress report."""
        stats = self.get_collection_stats()
        
        report = []
        report.append("="*60)
        report.append("RICK RUBIN DATA COLLECTION PROGRESS REPORT")
        report.append("="*60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall stats
        report.append(f"📊 OVERALL STATISTICS")
        report.append(f"Total Collections: {stats['total_collections']}")
        report.append("")
        
        # By source type
        report.append("📁 BY SOURCE TYPE:")
        for source_type, data in stats['by_source_type'].items():
            report.append(f"  - {source_type}: {data['count']} files, {data['words']:,} words")
        
        # Quality distribution
        report.append("\n📈 QUALITY DISTRIBUTION:")
        dist = stats['quality_distribution']
        report.append(f"  - Excellent (90+): {dist['excellent']}")
        report.append(f"  - Good (80-89): {dist['good']}")
        report.append(f"  - Fair (70-79): {dist['fair']}")
        report.append(f"  - Poor (<70): {dist['poor']}")
        
        # Processing status
        report.append("\n⚙️ PROCESSING STATUS:")
        proc = stats['processing_status']
        report.append(f"  - Cleaned: {proc['cleaned']}")
        report.append(f"  - Formatted: {proc['formatted']}")
        report.append(f"  - Exported: {proc['exported']}")
        
        # Recent exports
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT export_date, export_file, total_examples, avg_quality_score
                FROM export_history
                ORDER BY export_date DESC
                LIMIT 5
            """)
            recent_exports = cursor.fetchall()
        
        if recent_exports:
            report.append("\n📤 RECENT EXPORTS:")
            for export in recent_exports:
                date = datetime.fromisoformat(export[0]).strftime('%Y-%m-%d')
                report.append(f"  - {date}: {export[2]} examples, avg quality: {export[3]:.1f}")
        
        return '\n'.join(report)


def main():
    """Test the progress tracker."""
    tracker = ProgressTracker()
    
    # Test recording a collection
    source_id = tracker.record_collection(
        source_type="manual",
        source_name="Sample Rick Rubin Philosophy",
        file_path="data/manual_transcripts/sample_001_manual.json",
        word_count=226,
        quality_score=14.74
    )
    
    # Record quality metrics
    tracker.record_quality_metrics(source_id, {
        'rick_score': 4.42,
        'production_score': 19.91,
        'album_mentions': 2,
        'artist_mentions': 2,
        'overall_score': 14.74
    })
    
    # Update processing status
    tracker.update_processing_status(source_id, 'cleaned')
    
    # Generate report
    print(tracker.generate_report())


if __name__ == "__main__":
    main()
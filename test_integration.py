#!/usr/bin/env python3
"""
test_integration.py - Test RAG service integration with multi-agent system
Run: cd backend && source ../venv/bin/activate && python ../test_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add paths
backend_path = Path(__file__).parent / "backend"
src_path = Path(__file__).parent /"src"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "docker" / ".env")

async def test_rag_service():
    """Test the RAG audit service."""
    from app.services.rag_service import get_rag_service
    
    print("=" * 60)
    print("Testing RAG Audit Service")
    print("=" * 60)
    
    service = get_rag_service()
    
    # Test clause (BI regulation)
    test_clause = "Saldo maksimal untuk akun unverified adalah Rp 10.000.000"
    
    print(f"\nTest Clause: {test_clause}")
    print(f"Regulator: all")
    print(f"Testing...")
    
    try:
        result = await service.analyze_with_rag(
            clause=test_clause,
            regulator="all",
            top_k=3,
            use_cache=False
        )
        
        print(f"\n{'='*60}")
        print("RESULT:")
        print(f"{'='*60}")
        print(f"Final Status: {result.get('final_status')}")
        print(f"Confidence: {result.get('overall_confidence'):.2f}")
        print(f"Risk Score: {result.get('risk_score')}")
        print(f"Analysis Mode: {result.get('analysis_mode')}")
        print(f"Latency: {result.get('latency_ms')}ms")
        print(f"From Cache: {result.get('from_cache')}")
        
        if result.get('bi_verdict'):
            print(f"\n[BI Verdict]")
            bv = result['bi_verdict']
            print(f"  Status: {bv.get('verdict', bv.get('status'))}")
            print(f"  Confidence: {bv.get('confidence_score', bv.get('confidence', 0)):.2f}")
        
        if result.get('ojk_verdict'):
            print(f"\n[OJK Verdict]")
            ov = result['ojk_verdict']
            print(f"  Status: {ov.get('verdict', ov.get('status'))}")
            print(f"  Confidence: {ov.get('confidence_score', ov.get('confidence', 0)):.2f}")
        
        if result.get('violations'):
            print(f"\n[Violations]")
            for v in result['violations']:
                print(f"  - {v}")
        
        if result.get('recommendations'):
            print(f"\n[Recommendations]")
            for r in result['recommendations']:
                print(f"  - {r}")
        
        print(f"\n{'='*60}")
        print("TEST PASSED ✓")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_rag_service())
    sys.exit(0 if success else 1)
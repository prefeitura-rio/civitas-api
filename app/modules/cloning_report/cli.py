#!/usr/bin/env python3
"""
Command Line Interface for Civitas Cloning Detector
==================================================

Provides a convenient command-line interface for running cloning detection
analysis on license plate data.

Usage:
    civitas-detector --plate ABC1234 --start 2024-01-01 --end 2024-01-31
    civitas-detector --config config.json
    civitas-detector --help
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import json

import pandas as pd

from .report import ClonagemReportGenerator
from . import __version__


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Civitas License Plate Cloning Detection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --plate RJX1A61 --start 2024-07-01 --end 2024-07-31
  %(prog)s --plate ABC1234 --data-dir /path/to/data --output /path/to/output
  %(prog)s --config analysis_config.json
  %(prog)s --list-plates
        """
    )
    
    # Version
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    # Required arguments group
    analysis_group = parser.add_argument_group('Analysis Parameters')
    analysis_group.add_argument('--plate', '-p', type=str, 
                               help='License plate number to analyze (e.g., RJX1A61)')
    analysis_group.add_argument('--start', '-s', type=str,
                               help='Start date for analysis (YYYY-MM-DD)')
    analysis_group.add_argument('--end', '-e', type=str, 
                               help='End date for analysis (YYYY-MM-DD)')
    
    # Data configuration
    data_group = parser.add_argument_group('Data Configuration')
    data_group.add_argument('--data-dir', '-d', type=str, default='dados_placas',
                           help='Directory containing CSV data files (default: dados_placas)')
    data_group.add_argument('--data-file', '-f', type=str,
                           help='Specific CSV file path (overrides --data-dir/--plate)')
    
    # Output configuration
    output_group = parser.add_argument_group('Output Configuration')
    output_group.add_argument('--output', '-o', type=str, default='report',
                             help='Output directory for reports (default: report)')
    output_group.add_argument('--filename', type=str,
                             help='Custom output filename (default: {plate}.pdf)')
    output_group.add_argument('--no-plot', action='store_true',
                             help='Disable map generation (faster processing)')
    
    # Configuration file
    config_group = parser.add_argument_group('Configuration File')
    config_group.add_argument('--config', '-c', type=str,
                             help='JSON configuration file with analysis parameters')
    
    # Utility options
    utility_group = parser.add_argument_group('Utility Options')
    utility_group.add_argument('--list-plates', action='store_true',
                              help='List available license plates in data directory')
    utility_group.add_argument('--validate-data', action='store_true',
                              help='Validate data files without running analysis')
    utility_group.add_argument('--verbose', '-v', action='store_true',
                              help='Enable verbose output')
    
    return parser.parse_args()


def load_config(config_file):
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Configuration file not found: {config_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in configuration file: {e}")
        sys.exit(1)


def list_available_plates(data_dir):
    """List available license plates in data directory"""
    data_path = Path(data_dir)
    if not data_path.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    csv_files = list(data_path.glob("*.csv"))
    if not csv_files:
        print(f"📂 No CSV files found in {data_dir}")
        return
    
    print(f"📂 Available plates in {data_dir}:")
    print("─" * 40)
    
    for csv_file in sorted(csv_files):
        plate = csv_file.stem
        try:
            df = pd.read_csv(csv_file, parse_dates=['datahora'])
            records = len(df)
            date_range = f"{df['datahora'].min().date()} to {df['datahora'].max().date()}" if records > 0 else "No data"
            print(f"  📄 {plate:<12} | {records:>6} records | {date_range}")
        except Exception as e:
            print(f"  ❌ {plate:<12} | Error reading file: {e}")


def validate_data_file(file_path, verbose=False):
    """Validate a data file"""
    try:
        df = pd.read_csv(file_path, parse_dates=['datahora'])
        
        required_columns = ['datahora', 'latitude', 'longitude', 'logradouro', 'codcet']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"❌ Missing required columns: {missing_columns}")
            return False
        
        if verbose:
            print(f"✅ Data file validation passed")
            print(f"   Records: {len(df)}")
            print(f"   Date range: {df['datahora'].min().date()} to {df['datahora'].max().date()}")
            print(f"   Columns: {list(df.columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating data file: {e}")
        return False


def main():
    """Main CLI entry point"""
    args = parse_args()
    
    print(f"🚗 CIVITAS CLONING DETECTION SYSTEM v{__version__}")
    print("=" * 60)
    
    # Handle utility options
    if args.list_plates:
        list_available_plates(args.data_dir)
        return 0
    
    # Load configuration from file if provided
    if args.config:
        config = load_config(args.config)
        # Override command line args with config values
        for key, value in config.items():
            if hasattr(args, key) and getattr(args, key) is None:
                setattr(args, key, value)
    
    # Validate required arguments
    if not args.plate and not args.data_file:
        print("❌ Error: Either --plate or --data-file must be specified")
        print("Use --help for usage information")
        return 1
    
    if not args.start or not args.end:
        print("❌ Error: Both --start and --end dates must be specified")
        print("Use --help for usage information")
        return 1
    
    try:
        # Parse dates
        periodo_inicio = pd.Timestamp(args.start)
        periodo_fim = pd.Timestamp(args.end)
        
        if periodo_inicio >= periodo_fim:
            print("❌ Error: Start date must be before end date")
            return 1
        
        # Determine data file
        if args.data_file:
            data_file = Path(args.data_file)
            plate_number = data_file.stem
        else:
            data_file = Path(args.data_dir) / f"{args.plate}.csv"
            plate_number = args.plate
        
        if not data_file.exists():
            print(f"❌ Error: Data file not found: {data_file}")
            return 1
        
        # Validate data if requested
        if args.validate_data:
            print(f"🔍 Validating data file: {data_file}")
            if validate_data_file(data_file, verbose=args.verbose):
                print("✅ Data validation passed")
                return 0
            else:
                return 1
        
        # Load data
        if args.verbose:
            print(f"📊 Loading data from: {data_file}")
        
        df = pd.read_csv(data_file, parse_dates=['datahora'])
        print(f"📊 Data loaded: {len(df)} records for plate {plate_number}")
        print(f"📅 Analysis period: {periodo_inicio.date()} to {periodo_fim.date()}")
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output filename
        if args.filename:
            output_file = output_dir / args.filename
        else:
            output_file = output_dir / f"{plate_number}.pdf"
        
        # Run analysis
        print(f"🔍 Starting cloning detection analysis...")
        if args.verbose:
            print(f"   Detection algorithms: Temporal + Spatial clustering")
            print(f"   Speed threshold: 110 km/h")
            print(f"   Map generation: {'Disabled' if args.no_plot else 'Enabled'}")
        
        generator = ClonagemReportGenerator(df, plate_number, periodo_inicio, periodo_fim)
        
        # Generate report
        pdf_path = generator.generate(str(output_file))
        print(f"📄 Report generated: {pdf_path}")
        
        # Display summary
        print(f"\n📈 ANALYSIS SUMMARY")
        print("─" * 30)
        print(f"Total detections analyzed: {generator.total_deteccoes}")
        print(f"Suspicious pairs found: {generator.num_suspeitos}")
        
        if generator.num_suspeitos > 0:
            print(f"Peak suspicious day: {generator.dia_mais_sus}")
            print(f"Maximum suspicious speed: {generator.max_vel:.0f} km/h")
            print(f"Peak location: {generator.place_lider}")
            print(f"🚨 CLONING INDICATORS DETECTED")
        else:
            print(f"✅ No suspicious activity detected")
        
        print(f"\n🎯 Analysis complete! Check the generated PDF report for details.")
        return 0
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
